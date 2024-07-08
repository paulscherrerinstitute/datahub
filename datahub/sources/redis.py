try:
    import redis
except:
    redis = None

from datahub import *
from datahub.utils.data import *
from datahub.utils.checker import check_msg
import threading

_logger = logging.getLogger(__name__)

class Redis(Source):
    DEFAULT_URL = os.environ.get("REDIS_DEFAULT_URL", 'std-daq-build:6379')
    DEFAULT_BACKEND = os.environ.get("REDIS_DEFAULT_BACKEND", '0')

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, **kwargs):
        Source.__init__(self, url=url, backend=backend, path=path, **kwargs)
        if redis is None:
            raise Exception("PyRedis library not available")
        self.consumer_name = 'datahub'
        self.host, self.port = get_host_port_from_stream_address(self.url)
        self.db = self.backend
        self.messages = []


    def create_group(self, r, channels):
        group_name = generate_random_string(16)
        for channel in channels:
            try:
                r.xgroup_create(channel, group_name, mkstream=False)
            except Exception as e:
                _logger.warning(f"Error creating stream group: {str(e)}")
        return group_name

    def destroy_group(self, r, channels, group_name):
        for channel in channels:
            try:
                r.xgroup_destroy(channel, group_name)
            except Exception as e:
                _logger.warning(f"Error destroying stream group: {str(e)}")

    def run(self, query):
        partial_msg = query.get("partial_msg", True)
        channels = query.get("channels", [])
        size_align_buffer = query.get("size_align_buffer", 1000)
        filter = query.get("filter", None)

        with redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=False) as r:
            group_name = self.create_group(r, channels)
            try:
                sent_id = -1
                streams = {channel : ">" for channel in channels}
                aligned_data = MaxLenDict(maxlen=size_align_buffer)
                while not self.range.has_ended() and not self.aborted:
                    entries = r.xreadgroup(group_name, self.consumer_name, streams, count=5 * len(channels), block=100)
                    if entries:
                        for stream, messages in entries:
                            for message_id, message_data in messages:
                                channel = message_data[b'channel'].decode('utf-8')
                                timestamp = int(message_data[b'timestamp'].decode('utf-8'))
                                id = int(message_data[b'id'].decode('utf-8'))
                                data = message_data[b'value']
                                value = decode(data)
                                if id not in aligned_data:
                                    aligned_data[id] = {"timestamp": timestamp}
                                aligned_data[id][channel] = value
                                r.xack(stream, group_name, message_id)  # Acknowledge message

                        keys_in_order = sorted(list(aligned_data.keys()))
                        last_complete_id = -1
                        for id in [keys_in_order[i] for i in range(len(keys_in_order) - 1, 0, -1)]:
                            if len(aligned_data[id]) == (len(channels) + 1):
                                last_complete_id = id
                                break

                        for i in range(len(keys_in_order)):
                            id = keys_in_order[i]
                            complete = len(aligned_data[id]) == (len(channels) + 1)
                            done = complete or (last_complete_id > id) or (len(aligned_data) > (size_align_buffer / 2))
                            if done:
                                msg = aligned_data.pop(id)
                                if complete or partial_msg:
                                    if sent_id >= id:
                                        _logger.warning(f"Invalid ID {id} - last sent ID {sent_id}")
                                    else:
                                        timestamp = msg.pop("timestamp", None)
                                        if self.range.has_started():
                                            try:
                                                if not filter or self.is_valid(filter, id, timestamp, msg):
                                                    self.on_msg(id, timestamp, msg)
                                            except Exception as e:
                                                _logger.exception("Error receiving data: %s " % str(e))
                                        sent_id = id
                                else:
                                    logging.debug(f"Discarding partial message: {id}")
            finally:
                self.destroy_group(r, channels, group_name)
                self.close_channels()

    def is_valid(self, filter, id, timestamp, msg):
        try:
            return check_msg(msg, filter)
        except Exception as e:
            _logger.warning("Error processing filter: %s " % str(e))
            return False

    def on_msg(self, id, timestamp, msg):
        for channel_name in msg.keys():
            v = msg.get(channel_name, None)
            if v is not None:
                self.receive_channel(channel_name, v, timestamp, id, check_changes=True, check_types=True)

    def close(self):
        Source.close(self)

    def search(self, regex=None):
        with redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True) as r:
            if not regex:
                #info = r.info('keyspace')
                #return r.config_get('databases')
                return r.info('keyspace')
            else:
                cursor = '0'
                streams = []
                while cursor != 0:
                    cursor, keys = r.scan(cursor=cursor, match='*')
                    for key in keys:
                        if regex in key and r.type(key) == 'stream':
                                streams.append(key)
                return sorted(streams)

class RedisStream(Redis):

    def __init__(self, channels, filter=None, **kwargs):
        Redis.__init__(self, **kwargs)
        self.message_buffer = collections.deque(maxlen=10)
        self.condition = threading.Condition()
        self.req(channels, 0.0, 365 * 24 * 60 * 60, filter=filter, background=True)

    def close(self):
        Redis.close(self)

    def on_msg(self, id, timestamp, msg):
        with self.condition:
            self.message_buffer.append((id, timestamp, msg))
            self.condition.notify()

    def drain(self):
        with self.condition:
            self.message_buffer.clear()

    def receive(self, timeout=None):
        with self.condition:
            if not self.message_buffer:
                self.condition.wait(timeout)
            if self.message_buffer:
                return self.message_buffer.popleft()

    def forward_bsread(self, port, mode="PUB"):
        from datahub.utils.bsread import create_sender
        sender = create_sender(port, mode)
        try:
            while True:
                id, timestamp, data = self.receive()
                timestamp = (int(timestamp / 1e9), int(timestamp % 1e9)) #float(timestamp) / 1e9
                sender.send(data=data, pulse_id=id, timestamp=timestamp, check_data=True)
        finally:
            sender.close()

try:
    import redis
except:
    redis = None

from datahub import *
from datahub.utils.align import *

import threading

_logger = logging.getLogger(__name__)

class Redis(Source):
    """
    Retrieves data from the Redis or Dragonfly streams.
    """

    DEFAULT_URL = os.environ.get("REDIS_DEFAULT_URL", 'sf-daqsync-18:6379')
    DEFAULT_BACKEND = os.environ.get("REDIS_DEFAULT_BACKEND", '0')

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, **kwargs):
        """
        url (str, optional): Redis URL. Default value can be set by the env var REDIS_DEFAULT_URL.
        backend (str): Redis database. Default value can be set by the env var REDIS_DEFAULT_BACKEND.
        path (str, optional): hint for the source location in storage or displaying.
        """
        Source.__init__(self, url=url, backend=backend, path=path, **kwargs)
        if redis is None:
            raise Exception("PyRedis library not available")
        self.consumer_name = 'datahub'
        self.host, self.port = get_host_port_from_stream_address(self.url)
        self.db = self.backend
        self.messages = []


    def create_group(self, r, channels):
        group_name = generate_random_string(16)
        try:
            pipeline = r.pipeline()
            for channel in channels:
                pipeline.xgroup_create(channel, group_name, mkstream=False)
            pipeline.execute()
        except Exception as e:
            _logger.warning(f"Error creating stream group: {str(e)}")

        return group_name

    def destroy_group(self, r, channels, group_name):
        try:
            pipeline = r.pipeline()
            for channel in channels:
                pipeline.xgroup_destroy(channel, group_name)
            pipeline.execute()
        except Exception as e:
            _logger.warning(f"Error destroying stream group: {str(e)}")

    def run(self, query):
        partial_msg = query.get("partial_msg", True)
        utc_timestamp = query.get("utc_timestamp", True)
        channels = query.get("channels", [])
        size_buffer = query.get("size_buffer", 1000)
        filter = query.get("filter", None)
        align = Align(self.on_msg, channels, self.range, filter , partial_msg=partial_msg, size_buffer=size_buffer, utc_timestamp=utc_timestamp)

        with redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=False) as r:
            group_name = self.create_group(r, channels)
            try:
                streams = {channel : ">" for channel in channels}
                while not self.range.has_ended() and not self.aborted:
                    entries = r.xreadgroup(group_name, self.consumer_name, streams, count=5 * len(channels), block=100)
                    if entries:
                        for stream, messages in entries:
                            processed_ids = []
                            try:
                                for message_id, message_data in messages:
                                    channel = message_data[b'channel'].decode('utf-8')
                                    timestamp = int(message_data[b'timestamp'].decode('utf-8'))
                                    id = int(message_data[b'id'].decode('utf-8'))
                                    data = message_data[b'value']
                                    value = decode(data)
                                    align.add(id, timestamp, channel, value)
                                    processed_ids.append(message_id)
                            finally:
                                r.xack(stream, group_name, *processed_ids)
                        align.process()
            finally:
                self.destroy_group(r, channels, group_name)
                self.close_channels()

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
                #return r.config_get('databases')
                return r.info('keyspace')
            else:
                cursor = '0'
                streams = []
                match = f'*{regex}*' if regex else '*'
                while cursor != 0:
                    cursor, keys = r.scan(cursor=cursor, match=match)
                    for key in keys:
                        if regex in key and r.type(key) == 'stream':
                                if type(key)!=str:
                                    key = key.decode('utf-8')
                                streams.append(key)
                return sorted(streams)

class RedisStream(Redis):

    def __init__(self, channels, filter=None, queue_size=100,  **kwargs):
        Redis.__init__(self, **kwargs)
        self.message_buffer = collections.deque(maxlen=queue_size)
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

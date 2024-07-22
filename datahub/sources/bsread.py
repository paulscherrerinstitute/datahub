try:
    import bsread
except:
    bsread = None

from datahub import *
from datahub.utils.checker import check_msg
import collections
import threading

_logger = logging.getLogger(__name__)

class Bsread(Source):
    """
    Retrieves data from a Bsread source.
    """

    DEFAULT_URL = os.environ.get("BSREAD_DEFAULT_URL", None if (bsread is None) else bsread.DEFAULT_DISPATCHER_URL)

    def __init__(self, url=DEFAULT_URL, mode="SUB", path=None, **kwargs):
        """
        url (str, optional): Stream URL. Default value can be set by the env var BSREAD_DEFAULT_URL.
        mode (str, optional): "SUB" or "PULL"
        path (str, optional): hint for the source location in storage or displaying.
        """
        Source.__init__(self, url=url, path=path, **kwargs)
        if bsread is None:
            raise Exception("BSREAD library not available")
        self.mode = mode
        self.context = 0

    def run(self, query):
        mode = bsread.PULL if self.mode == "PULL" else bsread.SUB
        receive_timeout = query.get("receive_timeout", 3000)
        channels = query.get("channels", None)
        filter = query.get("filter", None)
        if not self.url or (self.url == bsread.DEFAULT_DISPATCHER_URL):
            host, port = None, 9999
            stream_channels = channels
        else:
            host, port = get_host_port_from_stream_address(self.url)
            stream_channels = None

        self.context = None

        with bsread.source(host=host, port=port, mode=mode, receive_timeout=receive_timeout, channels=stream_channels) as stream:
            self.context = stream.stream.context
            while not self.range.has_ended() and not self.aborted:
                data = stream.receive()
                if not data:
                    raise Exception("Received None message.")
                if self.range.has_started():
                    timestamp = create_timestamp(data.data.global_timestamp, data.data.global_timestamp_offset)
                    pulse_id = data.data.pulse_id
                    format_changed = data.data.format_changed
                    data=data.data.data

                    keys = channels if (channels and (len(channels)>0)) else data.keys()
                    msg = {channel: data[channel].value for channel in keys}

                    try:
                        if not filter or self.is_valid(filter, id, timestamp, msg):
                            self.on_msg(pulse_id, timestamp, msg, format_changed)
                    except Exception as e:
                        _logger.exception("Error receiving data: %s " % str(e))

            self.close_channels()
        if self.context:
            self.context.destroy()
            self.context = None

    def is_valid(self, filter, id, timestamp, msg):
        try:
            return check_msg(msg, filter)
        except Exception as e:
            _logger.warning("Error processing filter: %s " % str(e))
            return False

    def on_msg(self, id, timestamp, msg, format_changed):
        for channel in msg.keys():
            try:
                self.receive_channel(channel, msg[channel], timestamp, id, check_changes=format_changed)
            except Exception as ex:
                _logger.exception("Error receiving data: %s " % str(ex))


    def close(self):
        if self.context:
            self.context.destroy()
            self.context = None
        Source.close(self)


class BsreadStream(Bsread):

    def __init__(self, channels, filter=None, queue_size=100,  **kwargs):
        Bsread.__init__(self, **kwargs)
        self.message_buffer = collections.deque(maxlen=queue_size)
        self.condition = threading.Condition()
        self.req(channels, 0.0, 365 * 24 * 60 * 60, filter=filter, background=True)

    def close(self):
        Bsread.close(self)

    def on_msg(self, id, timestamp, msg, format_changed):
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


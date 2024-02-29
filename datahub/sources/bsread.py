try:
    import bsread
except:
    bsread = None

from datahub import *

_logger = logging.getLogger(__name__)

class Bsread(Source):
    DEFAULT_URL = os.environ.get("BSREAD_DEFAULT_URL", None if (bsread is None) else bsread.DEFAULT_DISPATCHER_URL)

    def __init__(self, url=DEFAULT_URL, mode="SUB", path=None, **kwargs):
        Source.__init__(self, url=url, path=path, **kwargs)
        if bsread is None:
            raise ("BSREAD library not available")
        self.mode = mode
        self.context = 0

    def run(self, query):
        mode = bsread.PULL if self.mode == "PULL" else bsread.SUB
        receive_timeout = query.get("receive_timeout", 3000)
        channels = query.get("channels", None)
        if self.url == bsread.DEFAULT_DISPATCHER_URL:
            host, port = None, None
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
                    if not channels:
                        channels = data.data.data.keys()
                    for channel_name in channels:
                        try:
                            v = data.data.data[channel_name].value
                            self.receive_channel(channel_name, v, timestamp, pulse_id, check_changes=format_changed)
                        except Exception as ex:
                            _logger.exception("Error receiving data: %s " % str(ex))
            self.close_channels()
        if self.context:
            self.context.destroy()
            self.context = None

    def close(self):
        if self.context:
            self.context.destroy()
            self.context = None
        Source.close(self)

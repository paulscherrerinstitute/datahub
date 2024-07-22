import zmq

from datahub import *

GENERATE_ID = False
_logger = logging.getLogger(__name__)

class Array10(Source):
    """
    Retrieves data from an Array10 stream.
    """
    DEFAULT_URL = os.environ.get("ARRAY10_DEFAULT_URL", None)
    def __init__(self, url=DEFAULT_URL, mode="SUB", path=None, reshape=False, **kwargs):
        """
        url (str, optional): Stream URL. Default value can be set by the env var ARRAY10_DEFAULT_URL.
        mode (str, optional): "SUB" or "PULL"
        path (str, optional): hint for the source location in storage or displaying.
        reshape (bool, optional): if True reshapes receiving array into 2d arrays/
        """
        Source.__init__(self, url=url, path=path, **kwargs)
        self.context = 0
        self.mode = mode
        self.ctx = None
        self.receiver = None
        self.pid = -1
        self.reshape = str_to_bool(str(reshape))

    def run(self, query):
        channels = query.get("channels", None)
        channel = channels[0] if (channels and len(channels)>0) else None
        try:
            self.connect()
            while not self.range.has_ended() and not self.aborted:
                data = self.receive()
                if not data:
                    raise Exception("Received None message.")
                if self.range.has_started():
                    pulse_id, array = data
                    name = channel if channel else (self.source if self.source else "Array10")
                    metadata = {} if self.reshape else {"width": self.shape[1], "height": self.shape[1]}
                    self.receive_channel(name, array, None, pulse_id if GENERATE_ID else None, check_changes=True, metadata=metadata)
        finally:
            self.close_channels()
            self.disconnect()

    def close(self):
        self.disconnect()
        Source.close(self)

    def connect(self):
        mode = zmq.PULL if self.mode == "PULL" else zmq.SUB
        self.ctx = zmq.Context()
        self.receiver = self.ctx.socket(mode)
        self.receiver.connect(self.url)
        if mode == zmq.SUB:
            self.receiver.subscribe("")
        self.message_count = 0

    def disconnect(self):
        try:
            self.receiver.close()
        except:
            pass
        try:
            self.ctx.term()
        except:
            pass
        finally:
            self.ctx = None

    def receive(self):
        try:
            header = self.receiver.recv()
            header = json.loads(''.join(chr(i) for i in header))
            self.shape = header.get("shape")
            self.dtype = header.get("type", "int8")
            self.source = header.get("source", "")
            data = self.receiver.recv()
            if data is not None:
                array = numpy.frombuffer(data, dtype=self.dtype)
                if self.reshape:
                    array = array.reshape(self.shape)
                self.pid = self.pid + 1
                return self.pid, array
        except Exception as e:
            _logger.warning("Error processing Array10: %s" % (str(e),))
            raise

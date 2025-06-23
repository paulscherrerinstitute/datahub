try:
    import zmq
except:
    zmq = None

from datahub import *

_logger = logging.getLogger(__name__)

class Array10(Source):
    """
    Retrieves data from an Array10 stream.
    """
    DEFAULT_URL = os.environ.get("ARRAY10_DEFAULT_URL", None)
    def __init__(self, url=DEFAULT_URL, mode="SUB", reshape=True, name=None, **kwargs):
        """
        url (str, optional): Stream URL. Default value can be set by the env var ARRAY10_DEFAULT_URL.
        mode (str, optional): "SUB" or "PULL"
        path (str, optional): hint for the source location in storage or displaying.
        reshape (bool, optional): if True (Default) reshapes receiving array into 2d arrays.
        name (str, optional): channel name of the receiving data - if None, uses stream's "source" field.
        """
        if zmq is None:
            raise Exception("pyzmq library not available")
        if not url.startswith("tcp://"):
            url = "tcp://" + url
        Source.__init__(self, url=url, name=name, **kwargs)
        self.context = 0
        self.mode = mode
        self.ctx = None
        self.receiver = None
        self.generated_pid = -1
        self.pid = -1
        self.reshape = str_to_bool(str(reshape))
        self.generate_id = False

    def run(self, query):
        self.generate_id = self.range.is_by_id()
        try:
            self.connect()
            pulse_id = -1
            init = True
            while not self.has_stream_finished(id=pulse_id+1):
                data = self.receive()
                if not data:
                    raise Exception("Received None message.")
                pulse_id, array = data
                if init:
                    init = False
                    self.range.set_init_id(pulse_id)
                if self.range.has_ended(id=pulse_id):
                    break
                if self.range.has_started(id=pulse_id):
                    name = self.name if self.name else (self.source if self.source else "Array10")
                    metadata = {} if self.reshape else {"width": self.shape[1], "height": self.shape[1]}
                    self.receive_channel(name, array, None, pulse_id, check_changes=True, metadata=metadata)
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
            self.frame = header.get("frame", None)
            data = self.receiver.recv()
            if data is not None:
                array = numpy.frombuffer(data, dtype=self.dtype)
                if self.reshape:
                    array = array.reshape(self.shape)
                self.generated_pid = self.generated_pid + 1
                pid = self.frame
                if pid is None and self.generate_id:
                    pid = self.generated_pid
                self.pid = pid
                return self.pid, array
        except Exception as e:
            _logger.warning("Error processing Array10: %s" % (str(e),))
            raise

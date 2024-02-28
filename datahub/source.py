from datahub import *
from threading import Thread, current_thread
import time
import inspect

_logger = logging.getLogger(__name__)

class Source():
    query_index = {}
    instances = set()

    def __init__(self, url=None, backend=None, query_path=None, search_path=None, auto_decompress=False, path=None,
                 known_backends=[], time_type="nano", **kwargs):
        self.url = url
        if query_path is not None:
            if not url.endswith(query_path):
                self.url = self.url + query_path

        self.search_url = url
        if search_path is not None:
            if not url.endswith(search_path):
                self.search_url = url + search_path

        self.channel_formats = {}
        self.channel_info = {}
        self.listeners = []
        if type(backend) == str:
            if backend.lower() in ["none", "null"]:
                backend = None
        self.backend = backend
        self.known_backends= known_backends
        if time_type.lower() in ["str", "string"]:
            self.time_type = "str"
        elif time_type.lower() in ["sec", "seconds", "inc"]:
            self.time_type = "sec"
        else:
            self.time_type = "nano"
        self.path = path
        self.query = None
        self.type = type(self).__name__.lower()
        self.query_index= None
        self.query_id = self.user_id = None
        self.processing_thread=None
        self.aborted = False
        self.running = False
        self.verbose = False
        self.parallel = False
        self.auto_decompress = auto_decompress
        Source.instances.add(self)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        self.__str__()

    def __str__(self):
        return "%s: %s" % (self.get_desc(), str(self.query))

    def get_desc(self):
        return "%s[%s]" % (self.get_id(), (str(self.backend) if self.backend else self.url))

    def set_id(self, id):
        self.user_id = id

    def get_id(self):
        if self.user_id:
            return str(self.user_id)
        return self.query_id

    def set_path(self, path):
        self.path = path

    def get_path(self):
        if self.path:
            return str(self.path)
        return self.get_id()

    def on_channel_header(self, name, typ, byteOrder, shape, channel_compression, has_id=True):
        self.channel_info[name] = [typ, byteOrder, shape, channel_compression, has_id]
        for listener in self.listeners:
            try:
                listener.on_channel_header(self, name, typ, byteOrder, shape, None if (self.auto_decompress) else channel_compression, has_id)
            except Exception as e:
                _logger.exception("Error creating channel on listener %s: %s" % (str(listener), str((name, typ, byteOrder, shape, channel_compression))))


    def on_channel_record(self, name, timestamp, pulse_id, value):
        if timestamp is None:
            timestamp = create_timestamp(time.time())

        timestamp = convert_timestamp(timestamp, self.time_type)

        if self.auto_decompress:
            [typ, byteOrder, shape, channel_compression, has_id] = self.channel_info[name]
            if channel_compression:
                value = decompress(value, name, channel_compression, shape, typ, byteOrder)
        for listener in self.listeners:
            try:
                listener.on_channel_record( self, name, timestamp, pulse_id, value)
            except Exception as e:
                _logger.exception("Error appending record on listener %s: %s" % (str(listener), str((name, timestamp, pulse_id, value))))

    def on_channel_completed(self, name):
        for listener in self.listeners:
            try:
                listener.on_channel_completed( self, name)
            except Exception as e:
                _logger.exception("Error completing channel on listener %s: %s" % (str(listener), str(name)))
        try:
            del self.channel_info[name]
        except:
            pass

    def on_start(self):
        for listener in self.listeners:
            try:
                listener.on_start(self)
            except Exception as e:
                _logger.exception("Error starting %s: %s" % (str(listener), str(e)))

    def on_stop(self, exception=None):
            for listener in self.listeners:
                try:
                    listener.on_stop(self, exception)
                except Exception as e:
                    _logger.exception("Error stopping %s: %s" % (str(listener), str(e)))

    def req(self, channels, start, end, background=False, **kwargs) -> None:
        query = {
            "channels": channels,
            "start": start,
            "end": end
        }
        query.update(kwargs)
        self.request(query, background)

    def request(self, query, background=False) -> None:
        if self.is_running():
            raise RuntimeError("Ongoing query")

        self.aborted = False
        self.query = query
        self.range = QueryRange(self.query)
        self.query_index = Source.query_index.get(self.type, -1) + 1
        Source.query_index[self.type]=self.query_index
        self.query_id = f"{self.type}_{self.query_index}"

        if background:
            self.processing_thread = Thread(target=self.do_run, args=(query,))
            self.processing_thread.setDaemon(True)
            self.processing_thread.start()
        else:
            self.processing_thread = None
            self.do_run(query)

    def join(self, timeout=None):
        if self.is_thread_running():
            self.processing_thread.join(timeout)

    def is_thread_running(self):
        return self.processing_thread and  self.processing_thread.is_alive()

    def is_running(self):
        return self.running

    def is_aborted(self):
        return self.aborted

    def is_in_processing_thread(self):
        return self.processing_thread == current_thread()


    def abort(self):
        self.aborted = True

    def do_run(self, query):
        self.running = True
        self.on_start()
        try:
            exc = None
            self.run(query)
        except Exception as e:
            exc = e
            raise
        finally:
            self.on_stop(exc)
            self.running = False

    def add_listener(self, listener):
        self.listeners.append(listener)

    def remove_listeners(self):
        self.listeners.clear()

    def close_listeners(self):
        for listener in self.listeners:
            listener.close()
        self.listeners.clear()

    #Utility methods to manage automatically calling on_channel_header on the first stream value
    def receive_channel(self, channel_name, value, timestamp, id, check_changes=False, check_types=False):
        existing = channel_name in self.channel_formats
        if check_types:
            if type(value) == int:
                value = numpy.int32(value)
            elif type(value) == float:
                value = numpy.float64(value)
            elif type(value) == bool:
                value = numpy.bool(value)
            elif isinstance(value, list):
                value = numpy.array(value)

        if not existing or check_changes:
            try:
                if isinstance(value, str):
                    fmt = typ, shape = "str", None
                else:
                    fmt = typ, shape = (value.dtype, value.shape)
            except:
                _logger.exception("Invalid type of channel %s: %s" % (str(channel_name), str(type(value))))
                return

            if fmt != self.channel_formats.get(channel_name, None):
                if existing:
                    self.on_channel_completed(channel_name)
                    _logger.warning("Channel %s changed type from %s to %s." % (str(channel_name), str(self.channel_formats.get(channel_name)), str(fmt)))
                    del self.channel_formats[channel_name]
                self.on_channel_header(channel_name, typ, Endianness.LITTLE, shape, None, id is not None)
                self.channel_formats[channel_name] = fmt

        self.on_channel_record(channel_name, timestamp, id, value)

    def close_channels(self):
        for channel_name in self.channel_formats.keys():
            self.on_channel_completed(channel_name)
        self.channel_formats = {}
        self.channel_info = {}

    def close(self):
        if self.is_thread_running():
            if not self.is_in_processing_thread():
                self.abort()
                self.join()
        self.close_channels()
        self.remove_listeners()
        if self in Source.instances:
            Source.instances.remove(self)

    #Virtuals
    def run(self, query):
        pass

    def search(self, regex):
        raise Exception(f"Search not implemented in {self.type}")

    def print_search(self, regex):
        print(json.dumps(self.search(regex), indent=4))

    def print_help(self):
        print(self.type+ " [" + self.get_source_meta(self.__class__) + " ...]")
        if self.known_backends:
            print ("Known backends:")
            for backend in self.known_backends:
                print (f"\t{backend}")

    @staticmethod
    def get_source_meta(cls):
        signature = inspect.signature(cls)
        pars = signature.parameters
        ret = "channels "
        for name, par in pars.items():
            if par.kind != inspect.Parameter.VAR_KEYWORD:
                if par.default == inspect.Parameter.empty:
                    ret = ret + name + " "
                else:
                    if type(par.default) == str:
                        dflt = "'" + par.default + "'"
                    else:
                        dflt = str(par.default)
                    ret = ret + name + "=" + dflt + " "
        ret = ret + ("start=None end=None")
        return ret

    @staticmethod
    def cleanup():
        for source in list(Source.instances):
            source.close()
from datahub import *
from threading import Thread, current_thread
import time
from datahub.utils.reflection import get_meta
import datahub.utils.timing as timing

_logger = logging.getLogger(__name__)

class Source():
    query_index = {}
    instances = set()

    def __init__(self, url=None, backend=None, query_path=None, search_path=None, auto_decompress=False, path=None,
                 known_backends=[], time_type="nano", name=None, **kwargs):
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
        self.last_rec_info = {}
        self.listeners = []
        self.set_backend(backend)
        self.known_backends= known_backends
        if time_type.lower() in ["str", "string"]:
            self.time_type = "str"
        elif time_type.lower() in ["sec", "secs", "seconds"]:
            self.time_type = "sec"
        elif time_type.lower() in ["milli", "millis", "milliseconds"]:
            self.time_type = "milli"
        else:
            self.time_type = "nano"
        self.path = path
        self.query = None
        self.type = type(self).__name__.lower()
        self.query_index= None
        self.query_id = self.user_id = None
        self.processing_thread = None
        self.sprocessing_thread = None
        self.aborted = False
        self.running = False
        self.verbose = False
        self.parallel = False
        self.downsample = False
        self.name = name
        self.auto_decompress = auto_decompress
        self.prefix = ""
        Source.instances.add(self)

    def get_backends(self):
        return self.known_backends
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __str__(self):
        return "%s: %s" % (self.get_desc(), str(self.query))

    def set_backend(self, backend):
        if type(backend) == str:
            if backend.strip().lower() in ["none", "null", ""]:
                backend = None
        self.backend = backend

    def get_backend(self):
        return self.backend

    def get_desc(self):
        return "%s[%s]" % (self.get_id(), (str(self.backend) if self.backend else self.url))

    def set_id(self, id):
        self.user_id = id

    def get_id(self):
        if self.user_id:
            return str(self.user_id)
        return self.query_id

    def get_name(self):
        if self.name:
            return self.name
        return self.get_id()

    def set_path(self, path):
        self.path = path

    def get_path(self):
        if self.path:
            return str(self.path)
        return self.get_id()

    def on_channel_header(self, name, typ, byteOrder, shape, channel_compression, metadata={}):
        if self.prefix:
            name = self.prefix + name
        self.channel_info[name] = [typ, byteOrder, shape, channel_compression, metadata]
        self.last_rec_info[name] = [0.0, 0] #timestamp, index

        for listener in self.listeners:
            try:
                listener.on_channel_header(self, name, typ, byteOrder, shape, None if (self.auto_decompress) else channel_compression, metadata)
            except Exception as e:
                _logger.exception("Error creating channel on listener %s: %s" % (str(listener), str((name, typ, byteOrder, shape, channel_compression))))

    def convert_time(self, timestamp):
        return convert_timestamp(timestamp, self.time_type)

    def adjust_type(self, value):
        if type(value) == int:
            return numpy.int64(value)
        elif type(value) == float:
            return numpy.float64(value)
        elif type(value) == bool:
            return numpy.bool(value)
        elif isinstance(value, list):
            return numpy.array(value)
        return value

    def on_channel_record(self, name, timestamp, pulse_id, value, **kwargs):
        if self.prefix:
            name = self.prefix + name
        if self.downsample:
            now = time.time()
            last_timestamp, last_index = self.last_rec_info[name]
            self.last_rec_info[name][1] = last_index + 1
            # interval is divider
            if self.modulo:
                if last_index % self.modulo != 0:
                    return
            #Downsampling is interval
            if self.interval:
                timespan = now - last_timestamp
                if timespan < self.interval:
                    return
            self.last_rec_info[name][0] = now

        if timestamp is None:
            timestamp = create_timestamp(time.time())

        timestamp = self.convert_time(timestamp)

        if self.auto_decompress:
            [typ, byteOrder, shape, channel_compression, metadata] = self.channel_info[name]
            if channel_compression:
                value = decompress(value, name, channel_compression, shape, typ, byteOrder)

        for listener in self.listeners:
            try:
                listener.on_channel_record(self, name, timestamp, pulse_id, value, **kwargs)
            except Exception as e:
                _logger.exception("Error appending record on listener %s: %s" % (str(listener), str((name, timestamp, pulse_id, value))))

    def on_channel_completed(self, name):
        if self.prefix:
            name = self.prefix + name
        if name in self.channel_info:
            for listener in self.listeners:
                try:
                    listener.on_channel_completed(self, name)
                except Exception as e:
                    _logger.exception("Error completing channel on listener %s: %s" % (str(listener), str(name)))

            try:
                del self.channel_info[name]
            except:
                pass

            try:
                del self.last_rec_info[name]
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
        if self.verbose:
            print (f"Requesting from {self.url}: ", query)

        self.aborted = False
        self.query = query
        self.range = QueryRange(self.query, self)

        self.modulo = self.query.get("modulo", None)
        if type(self.modulo) is str:
            try:
                self.modulo= int (self.modulo)
            except:
                raise RuntimeError("Invalid modulo: ", self.modulo)

        self.interval = self.query.get("interval", None)
        if type(self.interval) is str:
            try:
                self.interval = float(self.interval)
            except:
                raise RuntimeError("Invalid interval: ", self.interval)
        self.downsample = self.interval or self.modulo
        self.query_index = Source.query_index.get(self.type, -1) + 1
        Source.query_index[self.type]=self.query_index
        self.query_id = f"{self.type}_{self.query_index}"

        prefix = self.query.get("prefix", None)
        if prefix:
            has_prefix = str_to_bool(str(prefix))
            if has_prefix == True:
                self.prefix = self.get_name() + ":"
            elif has_prefix == False:
                self.prefix = ""
            else:
                self.prefix = prefix
        else:
            self.prefix = ""

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
    def receive_channel(self, channel_name, value, timestamp, id, check_changes=False, check_types=False, metadata={}, **kwargs):
        existing = channel_name in self.channel_formats
        if check_types:
            value = self.adjust_type(value);
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
                if metadata is None:
                    metadata = {}
                metadata["has_id"] = id is not None
                if existing:
                    self.on_channel_completed(channel_name)
                    _logger.warning("Channel %s changed type from %s to %s." % (str(channel_name), str(self.channel_formats.get(channel_name)), str(fmt)))
                    del self.channel_formats[channel_name]
                self.on_channel_header(channel_name, typ, Endianness.LITTLE, shape, None, metadata)
                self.channel_formats[channel_name] = fmt

        self.on_channel_record(channel_name, timestamp, id, value, **kwargs)

    def close_channels(self):
        for channel_name in self.channel_formats.keys():
            self.on_channel_completed(channel_name)
        self.channel_formats = {}
        self.channel_info = {}
        self.last_rec_info = {}

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
        search = self.search(regex)
        if type(search) == str:
            print(search)
        elif search is None:
            print("Empty")
        else:
            print(json.dumps(search, indent=4))

    def get_default_url(self):
        try:
            return getattr(self, "DEFAULT_URL")
        except:
            return None

    def get_default_backend(self):
        try:
            return getattr(self, "DEFAULT_BACKEND")
        except:
            return None

    def time_to_pulse_id(self, tm=time.time()):
        return timing.time_to_pulse_id(tm)

    def pulse_id_to_time(self, id):
        return timing.pulse_id_to_time(id)

    def print_help(self):
        meta = get_meta(self.__class__)
        print(f"Source Name: \n\t{self.type}")
        if (self.__class__.__doc__):
            print("Description:")
            print (f"\t{self.__class__.__doc__.strip()}")
        print(f"Arguments: \n\t[channels {meta}start=None end=None ...]")
        if (self.__class__.__init__.__doc__):
            print (self.__class__.__init__.__doc__)
        default_url = self.get_default_url()
        default_backend = self.get_default_backend()
        if default_url:
            print("Default URL:")
            print(f"\t{default_url}")
        if default_backend:
            print("Default Backend:")
            print(f"\t{default_backend}")
        backends = self.get_backends()
        if backends:
            print("Known Backends:")
            for backend in backends:
                print(f"\t{backend}")

    def _get_pandas(self):
        try:
            import pandas
            return pandas
        except:
            _logger.error("Pandas not installed: cannot report search as dataframe")
            return None

    @staticmethod
    def cleanup():
        for source in list(Source.instances):
            source.close()
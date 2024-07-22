from datahub import *
import io
from http.client import IncompleteRead

_logger = logging.getLogger(__name__)

KNOWN_BACKENDS = ["sf-databuffer", "sf-imagebuffer", "hipa-archive"]

class ProcessChannelHeaderResult:
    def __init__(self):
        self.error = False
        self.empty = False
        self.channel_info = None
        self.channel_name = None
        self.extractor_writer = None
        self.compression = None
        self.shape = None

def extractor_raw_data_blob(ts, pulse, buf, name, data_type, shape):
    return ts, pulse, buf

def extractor_basic_scalar(ts, pulse, buf, name, data_type, shape):
    value = numpy.frombuffer(buf, dtype=data_type)[0]
    return ts, pulse, value

def extractor_basic_shaped(ts, pulse, buf, name, data_type, shape):
    value = numpy.reshape(numpy.frombuffer(buf, dtype=data_type), shape)
    return ts, pulse, value

def resolve_struct_dtype(data_type: str, byte_order: str) -> str:
    if data_type is None:
        None
    data_type = data_type.lower()
    if data_type == "float64":
        dtype = 'd'
    elif data_type == "uint8":
        dtype = 'B'
    elif data_type == "int8":
        dtype = 'b'
    elif data_type == "uint16":
        dtype = 'H'
    elif data_type == "int16":
        dtype = 'h'
    elif data_type == "uint32":
        dtype = 'I'
    elif data_type == "int32":
        dtype = 'i'
    elif data_type == "uint64":
        dtype = 'Q'
    elif data_type == "int64":
        dtype = 'q'
    elif data_type == "float32":
        dtype = 'f'
    elif data_type == "bool8":
        dtype = '?'
    elif data_type == "bool":
        dtype = '?'
    elif data_type == "character":
        dtype = 'c'
    elif data_type == "string":
        dtype = "str"
    else:
        raise RuntimeError(f"unsupported dta type {data_type} {byte_order}")
    if byte_order is not None:
        x = byte_order.upper()
        if x not in ["LITTLE_ENDIAN", "BIG_ENDIAN"]:
            raise RuntimeError(f"unexpected byte order {byte_order}")
    if dtype != "str":
        if byte_order is not None and byte_order.upper() == "BIG_ENDIAN":
            dtype = ">" + dtype
        else:
            dtype = "<" + dtype
    return dtype



def process_channel_header(msg):
    name = msg["name"]
    ty = msg.get("type")
    # If no data could be found for this channel, then there is no `type` key and we stop here:
    if ty is None:
        res = ProcessChannelHeaderResult()
        res.empty = True
        res.channel_name = name
        return res
    dtype = resolve_struct_dtype(ty, msg.get("byteOrder"))
    if dtype is None:
        raise RuntimeError("unsupported dtype {} for channel {}".format(dtype, name))
    shape = list(reversed(msg.get("shape", [])))

    compression = msg.get("compression")
    # Older data api services indicate no-compression as `0` or even `"0"`
    # we handle these cases here
    if compression is not None:
        compression = int(compression)
    if compression == 0:
        compression = None
    if compression is None:
        if shape == [1]:
            # NOTE legacy compatibility: historically a shape [1] is treated as scalar
            # Which channels actually rely on this?
            _logger.warning(f"Received scalar-like shape, convert to true scalar  {name}")
            shape = []
        if len(shape) == 0:
            if dtype == "str":
                #extractor_writer = None
                extractor_writer = lambda ts, pulse, b: extractor_raw_data_blob(ts, pulse, b, name, data_type, shape)
            else:
                data_type = numpy.dtype(msg.get("type")).newbyteorder('<' if msg.get("byteOrder") == "LITTLE_ENDIAN" else ">")
                extractor_writer = lambda ts, pulse, b: extractor_basic_scalar(ts, pulse, b, name, data_type, shape)
        elif len(shape) > 0:
            if dtype == "str":
                raise RuntimeError("not yet supported, please report a channel that uses arrays of strings.")
            else:
                data_type = numpy.dtype(msg.get("type")).newbyteorder('<' if msg.get("byteOrder") == "LITTLE_ENDIAN" else ">")
                extractor_writer = lambda ts, pulse, b: extractor_basic_shaped(ts, pulse, b, name, data_type, shape)
        else:
            raise RuntimeError("unexpected  shape {shape}  channel {name}")
    elif compression == 1: #BITSHUFFLE_LZ4
        if dtype == "str":
            if len(shape) == 0:
                extractor_writer = lambda ts, pulse, b: extractor_raw_data_blob(ts, pulse, b, name, data_type, shape)
            else:
                raise RuntimeError("Arrays of strings not supported")
        else:
            if len(shape) == 0:
                raise RuntimeError(f"Compression not supported on scalar numeric data {name}  shape {shape}  dtype {dtype}")
            else:
                data_type = numpy.dtype(msg.get("type")).newbyteorder('<' if msg.get("byteOrder") == "LITTLE_ENDIAN" else ">")
                extractor_writer = lambda ts, pulse, b: extractor_raw_data_blob(ts, pulse, b, name, data_type, shape)
    else:
        raise RuntimeError(f"Compression type {compression} is not supported")

    res = ProcessChannelHeaderResult()
    res.channel_info = msg
    res.channel_name = name
    res.extractor_writer = extractor_writer
    res.compression = Compression.BITSHUFFLE_LZ4 if compression else None
    res.shape = shape
    return res

class Retrieval(Source):
    """
    Retrieves data from the old Retrieval.
    """

    DEFAULT_URL = os.environ.get("RETRIEVAL_DEFAULT_URL", "https://data-api.psi.ch/api/1")
    DEFAULT_BACKEND = os.environ.get("RETRIEVAL_DEFAULT_BACKEND", "sf-databuffer")

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, delay=1.0, **kwargs):
        """
        url (str, optional): Retrieval URL. Default value can be set by the env var RETRIEVAL_DEFAULT_URL.
        backend (str, optional): Retrieval backend. Default value can be set by the env var RETRIEVAL_DEFAULT_BACKEND.
        path (str, optional): hint for the source location in storage or displaying.
        delay (float, optional): Wait time for channels to be uploaded to storage before retrieval.
        """
        if url is None:
            raise RuntimeError("Invalid URL")

        if backend is not None:
            if backend not in KNOWN_BACKENDS:
                _logger.warning("Unknown backend: " + str(backend))

        Source.__init__(self, url=url, backend=backend, query_path="/query", search_path="/channels", path=path,
                        known_backends=KNOWN_BACKENDS, **kwargs)
        self.delay = delay

    def _get_range(self, start_expansion=False, end_expansion=False):
        #TODO: Only searching by date?
        start = self.range.get_start_str_iso()
        end = self.range.get_end_str_iso()
        return {
            "type": "date",
            "startDate": start,
            "endDate": end
        }

    def _get_request_status(self, url, reqid):
        url_status = re.sub(r"/[^/]+$", "/requestStatus/" + reqid, url)
        return get_json(url_status)

    def _get_request_status_from_immediate_error(self, url, response):
        response_body = response.read(1024).decode()
        try:
            err = json.loads(response_body)
            reqid = err["requestId"]
            url_status = re.sub(r"/[^/]+$", "/requestStatus/" + reqid, url)
            err = get_json(url_status)
            if err: _logger.error(err)
            return err
        except:
            _logger.error(f"can not parse error message as json:\n{response_body}")
            raise

    def run(self, query):
        self.range.wait_end(delay=1.0)

        json = {}
        json["channels"] = query["channels"]
        json["range"] = self._get_range()
        if self.backend is not None:
            json["defaultBackend"] = self.backend
        conn = http_data_query(json, self.url)
        try:
            response = conn.getresponse()
            if response.status != 200:
                _logger.error(f"Unable to retrieve data: {response.status}")
                status = self._get_request_status_from_immediate_error(self.url, response)
                raise RuntimeError(f"Unable to retrieve data  {str(status)}")
            try:
                self.read(io.BufferedReader(response))
                reqid = response.headers["x-daqbuffer-request-id"]
                stat = self._get_request_status(self.url, reqid)
                if stat.get("errors") is not None:
                    raise RuntimeError("request error")
            except (ProtocolError, RuntimeError) as e:
                _logger.error(f"error during request  {e}")
                reqid = response.headers["x-daqbuffer-request-id"]
                stat = self._get_request_status(self.url, reqid)
                _logger.error(f"request status: {stat}")
                raise
        finally:
            conn.close()


    def read(self, stream):
        try:
            return self.read_throwing(stream)
        except IncompleteRead:
            _logger.error("unexpected end of input")
            raise ProtocolError()

    def read_throwing(self, stream):
        current_channel_info = None
        current_channel_name = None
        header = None

        while True:
            bytes_read = stream.read(4)
            if len(bytes_read) != 4:
                if current_channel_name is not None:
                    self.on_channel_completed(current_channel_name)
                break
            length = struct.unpack('>i', bytes_read)[0]
            bytes_read = stream.read(length)
            if len(bytes_read) != length:
                raise RuntimeError("unexpected EOF")
            mtype = struct.unpack('b', bytes_read[:1])[0]

            if mtype == 1 and (current_channel_info is not None):
                timestamp = struct.unpack('>q', bytes_read[1:9])[0]
                pulse_id = struct.unpack('>q', bytes_read[9:17])[0]
                raw_data_blob = bytes_read[17:]
                timestamp, pulse_id, value = header.extractor_writer(timestamp, pulse_id, raw_data_blob)
                self.on_channel_record(current_channel_name, timestamp, pulse_id, value)

            # Channel header message
            # A json message that specifies among others data type, shape, compression flags.
            elif mtype == 0:
                if current_channel_name is not None:
                    self.on_channel_completed(current_channel_name)
                current_channel_name = None
                current_channel_info = None
                try:
                    msg = json.loads(bytes_read[1:])
                    res = process_channel_header(msg)
                except Exception as e:
                    raise RuntimeError("Can not process channel header") from e
                if res.error:
                    _logger.error(f"Can not parse channel header message: {msg}")
                elif res.empty:
                    _logger.debug(f"No data for channel {res.channel_name}")
                else:
                    if "type" not in msg:
                        raise RuntimeError()
                    header = res
                    current_channel_info = res.channel_info
                    current_channel_name = res.channel_name
                    if current_channel_info.get('shape', None) is not None:
                         current_channel_info['shape'].reverse()
                    self.on_channel_header(current_channel_name, current_channel_info['type'],
                                                    current_channel_info['byteOrder'],
                                                    current_channel_info['shape'],
                                                    res.compression)
            bytes_read = stream.read(4)
            length_check = struct.unpack('>i', bytes_read)[0]
            if length_check != length:
                raise RuntimeError(f"corrupted file reading {length} {length_check}")

    def search(self, regex):
        import requests
        res = requests.get(self.search_url, {"regex": regex})
        res.raise_for_status()
        ret = res.json()
        return ret


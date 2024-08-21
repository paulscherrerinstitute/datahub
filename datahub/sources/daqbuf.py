from datahub import *
import io
from threading import Thread
from http.client import IncompleteRead


_logger = logging.getLogger(__name__)

class Daqbuf(Source):
    """
    Retrieves data from a Daqbuf service (new retrieval).
    """

    DEFAULT_URL = os.environ.get("DAQBUF_DEFAULT_URL", "https://data-api.psi.ch/api/4")
    DEFAULT_BACKEND = os.environ.get("DAQBUF_DEFAULT_BACKEND", "sf-databuffer")

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, delay=1.0, cbor=True, parallel=False, **kwargs):
        """
        url (str, optional): Daqbuf URL. Default value can be set by the env var DAQBUF_DEFAULT_URL.
        backend (str, optional): Daqbuf backend. Default value can be set by the env var DAQBUF_DEFAULT_BACKEND.
        path (str, optional): hint for the source location in storage or displaying.
        delay (float, optional): Wait time for channels to be uploaded to storage before retrieval.
        cbor (bool, optional): if True (default) retrieves data as CBOR, otherwise as JSON.
        parallel (bool, optional): if True performs the retrieval of multiple channels in differt threads.
        """
        if url is None:
            raise RuntimeError("Invalid URL")
        Source.__init__(self, url=url, backend=backend, query_path="/events",  search_path="/search/channel", path=path,
                        known_backends=None, **kwargs)
        self.base_url = url
        self.binned_url = self.base_url + "/binned"
        self.known_backends = self.get_backends()
        self.delay = delay
        self.cbor = str_to_bool(str(cbor))
        self.parallel = str_to_bool(str(parallel))
        if self.cbor:
            try:
                import cbor2
                self.cbor = cbor2
            except:
                _logger.error("cbor2 not installed: JSON fallback on Daqbuf searches")
                self.cbor = None

    def pulse_id_to_time(self, id):
        import requests
        response = requests.get(self.base_url + "/map/pulse/sf-databuffer/" + str(id))
        if response.status_code != 200:
            raise RuntimeError("Unable to retrieve data from server: ", response)
        data = response.text
        nanos = int(data)
        secs = convert_timestamp(nanos, "sec")
        ret = round(secs, PULSE_ID_INTERVAL_DEC)
        return ret

    def get_backends(self):
        try:
            if self.known_backends is None:
                import requests
                response = requests.get(self.base_url + "/backend/list")
                ret = response.json()
                backends = ret["backends_available"]
                self.known_backends = [backend["name"] for backend in backends]
            return self.known_backends
        except Exception as e:
            _logger.exception(e)
            return []

    def read(self, stream, channel):
        try:
            current_channel_name = None

            while True:
                bytes_read = stream.read(4)
                if len(bytes_read) != 4:
                    break
                length = struct.unpack('<i', bytes_read)[0]

                bytes_read = stream.read(12) #PADDING
                if len(bytes_read) != 12:
                    break

                bytes_read = stream.read(length)
                if len(bytes_read) != length:
                    raise RuntimeError("unexpected EOF")
                parsed_data = self.cbor.loads(bytes_read)

                padding = padding = (8 - (length % 8)) % 8
                bytes_read = stream.read(padding) #PADDING
                if len(bytes_read) != padding:
                    break

                if type(parsed_data) != dict:
                    raise RuntimeError("Invalid cbor frame: " + str(type(parsed_data)))

                if parsed_data.get("error", None) :
                    raise Exception(parsed_data.get("error"))

                if not parsed_data.get ("type","") == 'keepalive':
                    tss = parsed_data.get('tss', [])
                    pulses = parsed_data.get('pulses', [])
                    values = parsed_data.get('values', [])
                    scalar_type = parsed_data.get('scalar_type', None)
                    rangeFinal = parsed_data.get('rangeFinal', False)

                    if scalar_type:
                        nelm = len(values)
                        for i in range(nelm):
                            timestamp = tss[i]
                            pulse_id = pulses[i]
                            value = values[i]
                            self.receive_channel(channel, value, timestamp, pulse_id, check_changes=False, check_types=True)
                            current_channel_name = channel
                    if rangeFinal:
                        break
                    elif not scalar_type:
                        raise RuntimeError("Invalid cbor frame keys: " + str(parsed_data.keys()))

                    if not self.is_running() or self.is_aborted():
                        raise RuntimeError("Query has been aborted")

        except IncompleteRead:
            _logger.error("Unexpected end of input")
            raise ProtocolError()
        finally:
            if current_channel_name:
                self.on_channel_completed(current_channel_name)

    def run_channel(self, channel, cbor, bins=None, last=None, conn=None):
        query = dict()
        query["channelName"] = channel
        query["begDate"] = self.range.get_start_str_iso()
        query["endDate"] = self.range.get_end_str_iso()
        query["backend"] = self.backend
        if last is not None:
            query["oneBeforeRange"] = "true" if last else "false"

        if cbor:
            create_connection = conn is None
            conn = http_data_query(query, self.url, method="GET", accept="application/cbor-framed", conn=conn)
            try:
                response = conn.getresponse()
                if response.status != 200:
                    raise RuntimeError(f"Unable to retrieve data from server: {response.reason} [{response.status}]")
                try:
                    self.read(io.BufferedReader(response), channel)
                except Exception as e:
                    _logger.exception(e)
                    raise
            finally:
                if create_connection:
                    conn.close()

        else:
            import requests
            if bins:
                query["binCount"] = bins
                response = requests.get(self.binned_url, query)
                # Check for successful return of data
                if response.status_code != 200:
                    raise RuntimeError("Unable to retrieve data from server: ", response)
                data = response.json()
                nelm = len(data['avgs'])
                for i in range(nelm):
                    secs1 = data['tsAnchor'] + float(data['ts1Ms'][i]) / 1000.0
                    timestamp1 = create_timestamp(secs1, data['ts1Ns'][i])
                    secs2 = data['tsAnchor'] + float(data['ts2Ms'][i]) / 1000.0
                    timestamp2 = create_timestamp(secs2, data['ts2Ns'][i])
                    avg = data['avgs'][i]
                    max = self.adjust_type(data['maxs'][i])
                    min = self.adjust_type(data['mins'][i])
                    count = self.adjust_type(data['counts'][i])
                    start = self.convert_time(timestamp1)
                    end = self.convert_time(timestamp2)

                    value = avg
                    timestamp = int((timestamp1 + timestamp2)/2)
                    args = {"bins":bins, "min":numpy.float64(min), "max":numpy.float64(max), "count":numpy.int64(count), "start":start, "end": end}
                    self.receive_channel(channel, value, timestamp, None, check_changes=False, check_types=True, metadata={"bins":bins}, **args)
            else:
                response = requests.get(self.url, query)
                # Check for successful return of data
                if response.status_code != 200:
                    raise RuntimeError("Unable to retrieve data from server: ", response)
                data = response.json()
                nelm = len(data['values'])
                for i in range(nelm):
                    secs = data['tsAnchor'] + float(data['tsMs'][i]) / 1000.0
                    timestamp = create_timestamp(secs, data['tsNs'][i])
                    pulse_id = data['pulseAnchor'] + data['pulseOff'][i]
                    value = data['values'][i]
                    self.receive_channel(channel, value, timestamp, pulse_id, check_changes=False, check_types=True)
            self.on_channel_completed(channel)


    def run(self, query):
        self.range.wait_end(delay=self.delay)
        channels = query.get("channels", [])
        bins = query.get("bins", None)
        last = query.get("last", None)
        cbor = self.cbor and not bins
        if isinstance(channels, str):
            channels = [channels, ]
        conn = None
        threads = []
        try:
            if self.parallel:
                for channel in channels:
                    thread = Thread(target=self.run_channel, args=(channel, cbor, bins, last))
                    thread.setDaemon(True)
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
            else:
                if cbor:
                    conn = create_http_conn(self.url)
                for channel in channels:
                    self.run_channel(channel, cbor, bins, last, conn)
        finally:
            if conn:
                conn.close()
            self.close_channels()

    def search(self, regex):
        import requests
        if not regex:
            return self.get_backends()
        else:
            cfg = {
                "nameRegex": regex
            }
            if self.backend:
                cfg["backend"] = self.backend
            response = requests.get(self.search_url, params=cfg)
            ret = response.json()

            if not self.verbose:
                channels = ret.get("channels", [])
                pd = self._get_pandas()
                if pd is None:
                    ret = [d["name"] for d in ret.get("channels", [])]
                else:
                    if (len(channels)>0):
                        header = list(channels[0].keys()) if len(channels) > 0 else []
                        data = [d.values() for d in channels]
                        df = pd.DataFrame(data, columns=header)
                        df = df.sort_values(by=["backend", "name"])
                        columns_to_display = ["backend", "name", "seriesId", "type", "shape"]
                        ret = df[columns_to_display].to_string(index=False)
                    else:
                        return None
            return ret


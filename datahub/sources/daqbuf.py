from datahub import *
import io
from threading import Thread
from http.client import IncompleteRead
import http

_logger = logging.getLogger(__name__)

class Daqbuf(Source):
    """
    Retrieves data from a Daqbuf service (new retrieval).
    """
    API_VERSION = "1.0"
    DEFAULT_URL = os.environ.get("DAQBUF_DEFAULT_URL", "https://data-api.psi.ch/api/4")
    DEFAULT_BACKEND = os.environ.get("DAQBUF_DEFAULT_BACKEND", "sf-databuffer")

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, delay=1.0, cbor=True, parallel=True, streamed=True, **kwargs):
        """
        url (str, optional): Daqbuf URL. Default value can be set by the env var DAQBUF_DEFAULT_URL.
        backend (str, optional): Daqbuf backend. Default value can be set by the env var DAQBUF_DEFAULT_BACKEND.
        path (str, optional): hint for the source location in storage or displaying.
        delay (float, optional): Wait time for channels to be uploaded to storage before retrieval.
        cbor (bool, optional): if True (default) retrieves data as CBOR, otherwise as JSON.
        parallel (bool, optional): if True (default) performs the retrieval of multiple channels in differt threads.
        """
        if url is None:
            raise RuntimeError("Invalid URL")
        Source.__init__(self, url=url, backend=backend, query_path="/events",  search_path="/search/channel", path=path,
                        known_backends=None, **kwargs)
        self.base_url = url
        self.binned_url = self.base_url + "/binned"
        self.known_backends = self.get_backends()
        self.delay = delay
        self.cbor = str_to_bool(cbor)
        self.parallel = str_to_bool(parallel)
        self.streamed = str_to_bool(streamed)
        self.add_headers = {"daqbuf-api-version":Daqbuf.API_VERSION }
        self.headers = get_default_header()
        self.headers.update(self.add_headers)

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
        secs = convert_timestamp(nanos, "sec", "nano")
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

    def read_cbor(self, stream, channel):
        try:
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
                data = self.cbor.loads(bytes_read)

                padding = padding = (8 - (length % 8)) % 8
                bytes_read = stream.read(padding) #PADDING
                if len(bytes_read) != padding:
                    break

                if type(data) != dict:
                    raise RuntimeError("Invalid cbor frame: " + str(type(data)))

                if data.get("error", None) :
                    raise Exception(data.get("error"))

                if not data.get ("type","") == 'keepalive':
                    values = data.get('values', [])
                    tss = data.get('tss', [])
                    pulses = data.get('pulses', [])
                    scalar_type = data.get('scalar_type', None)
                    rangeFinal = data.get('rangeFinal', False)
                    valuestrings = data.get('valuestrings', [])
                    enums = len(valuestrings) == len(values)

                    if scalar_type:
                        nelm = len(values)
                        for i in range(nelm):
                            timestamp = tss[i] if len(tss)>i else None
                            pulse_id = pulses[i] if len(pulses)>i else None
                            value = values[i]
                            if enums:
                                value = Enum(value,valuestrings[i])
                            self.receive_channel(channel, value, timestamp, pulse_id, check_changes=False, check_types=True)
                    if rangeFinal:
                        break
                    elif not scalar_type:
                        raise RuntimeError("Invalid cbor frame keys: " + str(data.keys()))

                    if not self.is_running() or self.is_aborted():
                        raise RuntimeError("Query has been aborted")

        except IncompleteRead:
            _logger.error("Unexpected end of input")
            raise ProtocolError()


    def read_json(self, stream, channel, bins=None):
        try:
            while True:
                length = stream.readline()
                if len(length) == 0:
                    break
                length = int(length)
                bytes_read = stream.read(length)
                if len(bytes_read) != length:
                    raise RuntimeError("unexpected EOF")
                _ = stream.read(1) #newline
                data = json.loads(bytes_read)
                if type(data) == str:
                    raise RuntimeError ("Error: " + data)
                if data.get("error", None) :
                    raise Exception(data.get("error"))
                if not data.get ("type","") == 'keepalive':
                    rangeFinal = data.get('rangeFinal', False)
                    self.read_json_single(data, channel, bins)
                    if rangeFinal:
                        break
                    if not self.is_running() or self.is_aborted():
                        raise RuntimeError("Query has been aborted")

        except IncompleteRead:
            _logger.error("Unexpected end of input")
            raise ProtocolError()

    def read_json_single(self, data, channel, bins=None):
        if bins:
            avgs = data['avgs']
            nelm = len(avgs)
            tsAnchor = data['tsAnchor']
            ts1Ms = data['ts1Ms']
            ts2Ms = data['ts2Ms']
            ts1Ns = data['ts1Ns']
            ts2Ns = data['ts2Ns']
            maxs = data['maxs']
            mins = data['mins']
            counts = data['counts']
            for i in range(nelm):
                secs1 = tsAnchor + float(ts1Ms[i]) / 1000.0
                secs2 = tsAnchor + float(ts2Ms[i]) / 1000.0
                timestamp1 = create_timestamp(secs1, 0.0 if (ts1Ns is None) else ts1Ns[i])
                timestamp2 = create_timestamp(secs2, 0.0 if (ts2Ns is None) else ts2Ns[i])
                avg = avgs[i]
                max = self.adjust_type(maxs[i])
                min = self.adjust_type(mins[i])
                count = self.adjust_type(counts[i])

                value = avg
                timestamp = int((timestamp1 + timestamp2) / 2)
                args = {"bins": bins, "min": numpy.float64(min), "max": numpy.float64(max), "count": numpy.int64(count),
                        "start": timestamp1, "end": timestamp2}
                self.receive_channel(channel, value, timestamp, None, check_changes=False, check_types=True,
                                     metadata={"bins": bins}, **args)
        else:
            nelm = len(data['values'])
            for i in range(nelm):
                secs = data['tsAnchor'] + float(data['tsMs'][i]) / 1000.0
                timestamp = create_timestamp(secs, data['tsNs'][i])
                pulse_id = data['pulseAnchor'] + data['pulseOff'][i]
                value = data['values'][i]
                self.receive_channel(channel, value, timestamp, pulse_id, check_changes=False, check_types=True)

    def check_response(self, response, channel):
        if type(response) == http.client.HTTPResponse:
            status = response.status
        else:
            status = response.status_code
        if status != 200:
            try:
                if type(response) == http.client.HTTPResponse:
                    body = json.loads(response.read().decode('utf-8'))
                else:
                    body = response.json()
                message = body["message"].capitalize()
                requestid = body["requestid"]
                if not message:
                    raise Exception()
                ex = RuntimeError(f"{message}\nChannel: {channel}\nRequest ID: {requestid}");
            except:
                ex = RuntimeError(f"Error retrieving data: {response.reason} [{status}]\nChannel: {channel}")
            raise ex

    def run_channel(self, channel, backend, cbor, bins=None, last=None, conn=None):
        query = dict()
        if channel.isdigit():
            query["seriesId"] = channel
        else:
            query["channelName"] = channel
        query["begDate"] = self.range.get_start_str_iso()
        query["endDate"] = self.range.get_end_str_iso()
        query["backend"] = backend
        if last is not None:
            query["oneBeforeRange"] = "true" if last else "false"
        if bins:
            if (type(bins) == str) and len(bins)>1 and bins[-1].isalpha():
                query["binWidth"] = bins
            else:
                query["binCount"] = int(bins)

        streamed = self.streamed or cbor
        create_connection = streamed and (conn is None)
        url = self.binned_url if bins else self.url
        if streamed:
            conn = http_data_query(query, url,method="GET",
                                   accept="application/cbor-framed" if cbor else "application/json-framed",
                                   conn=conn,
                                   add_headers=self.add_headers)
        try:
            if cbor:
                response = conn.getresponse()
                self.check_response(response, channel)
                try:
                    self.read_cbor(io.BufferedReader(response), channel)
                except Exception as e:
                    _logger.exception(e)
                    raise
            else:
                if bins:
                    if self.streamed:
                        response = conn.getresponse()
                        self.check_response(response, channel)
                        try:
                            self.read_json(io.BufferedReader(response), channel, bins)
                        except Exception as e:
                            _logger.exception(e)
                            raise
                    else:
                        import requests
                        response = requests.get(url , query, headers=self.headers)
                        # Check for successful return of data
                        self.check_response(response, channel)
                        data = response.json()
                        self.read_json_single(data, channel, bins)
                else:
                    if self.streamed:
                        response = conn.getresponse()
                        self.check_response(response, channel)
                        try:
                            self.read_json(io.BufferedReader(response), channel)
                        except Exception as e:
                            _logger.exception(e)
                            raise
                    else:
                        import requests
                        response = requests.get(url , query, headers=self.headers)
                        self.check_response(response, channel)
                        data = response.json()
                        self.read_json_single(data, channel)
        finally:
            if self.receiving_channel(channel):
                self.on_channel_completed(channel)
            if create_connection and conn:
                conn.close()

    def run(self, query):
        self.range.wait_end(delay=self.delay)
        channels = query.get("channels", [])
        bins = query.get("bins", None)
        last = query.get("last", None)
        backend = query.get("backend", self.backend)
        cbor = self.cbor and not bins
        streamed = self.streamed or cbor
        if isinstance(channels, str):
            channels = [channels, ]
        conn = None
        threads = []
        try:
            if self.parallel:
                for channel in channels:
                    thread = Thread(target=self.run_channel, args=(channel, backend, cbor, bins, last))
                    thread.setDaemon(True)
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
            else:
                if streamed:
                    conn = create_http_conn(self.binned_url if bins else self.url)
                for channel in channels:
                    self.run_channel(channel, backend, cbor, bins, last, conn)
        finally:
            if conn:
                conn.close()
            self.close_channels()

    def search(self, regex, case_sensitive=True):
        import requests
        if not regex:
            return self.get_backends()
        else:
            cfg = {
                "nameRegex": regex,
                "icase" : "false" if case_sensitive else "true"
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


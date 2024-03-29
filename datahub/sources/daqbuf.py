from datahub import *
import io
from threading import Thread
from http.client import IncompleteRead


_logger = logging.getLogger(__name__)

KNOWN_BACKENDS = ["sf-databuffer"]

class Daqbuf(Source):
    DEFAULT_URL = os.environ.get("DAQBUF_DEFAULT_URL", "https://data-api.psi.ch/api/4")
    DEFAULT_BACKEND = os.environ.get("DAQBUF_DEFAULT_BACKEND", "sf-databuffer")

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, delay=1.0, cbor=True, parallel=False, **kwargs):
        if url is None:
            raise RuntimeError("Invalid URL")
        Source.__init__(self, url=url, backend=backend, query_path="/events",  search_path="/search/channel", path=path,
                        known_backends=KNOWN_BACKENDS, **kwargs)
        self.delay = delay
        self.cbor = str_to_bool(str(cbor))
        self.parallel = str_to_bool(str(parallel))
        try:
            import cbor2
            self.cbor = cbor2
        except:
            _logger.error("cbor2 not installed: JSON fallback on Daqbuf searches")
            self.cbor = None



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

    def run_channel(self, channel, conn=None):
        query = dict()
        query["channelName"] = channel
        query["begDate"] = self.range.get_start_str_iso()
        query["endDate"] = self.range.get_end_str_iso()
        query["backend"] = self.backend

        if self.cbor:
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
        if isinstance(channels, str):
            channels = [channels, ]
        conn = None
        threads = []
        try:
            if self.parallel:
                for channel in channels:
                    thread = Thread(target=self.run_channel, args=(channel, ))
                    thread.setDaemon(True)
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
            else:
                if self.cbor:
                    conn = create_http_conn(self.url)
                for channel in channels:
                    self.run_channel(channel, conn)
        finally:
            if conn:
                conn.close()
            self.close_channels()

    def search(self, regex):
        import requests
        if not regex:
            return self.known_backends
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


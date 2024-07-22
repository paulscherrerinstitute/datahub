try:
    import epics
except:
    epics = None

from datahub import *

GENERATE_ID = False

_logger = logging.getLogger(__name__)

class Channel:
    def __init__(self, name, source):
        if epics is None:
            raise Exception("EPICS library not available")
        self.name = name
        self.channel = epics.PV(name, auto_monitor=True)
        self.id = 0
        self.source = source
        # channel.wait_for_connection(config.EPICS_TIMEOUT)

    def start(self):
        def callback(value, timestamp, status, **kwargs):
            channel_name =self.name
            timestamp = create_timestamp(timestamp)
            self.source.receive_channel(self.name, value, timestamp, self.pulse_id if GENERATE_ID else None, check_types=True)
            self.id = self.id + 1
        self.channel.add_callback(callback)

    def stop(self):
        self.channel.clear_callbacks()


    def close(self):
        try:
            self.channel.disconnect()
        except:
            pass

class Epics(Source):
    """
    Retrieves data from the EPICS channels.
    """
    DEFAULT_URL = None
    def __init__(self, url=DEFAULT_URL, path=None, **kwargs):
        """
        url (str, optional): if defined sets the EPICS_CA_ADDR_LIST.
        path (str, optional): hint for the source location in storage or displaying.
        """
        Source.__init__(self, url=url, path=path, **kwargs)
        if self.url:
            os.environ["EPICS_CA_ADDR_LIST"] = self.url

    def run(self, query):
        channels_names = query.get("channels", [])
        channels = []
        for name in channels_names:
            channel = Channel(name, self)
            channels.append(channel)
        try:
            self.range.wait_start()
            for channel in channels:
                channel.start()
            while self.range.is_running() and not self.aborted:
                time.sleep(0.1)
            for channel in channels:
                channel.stop()
            self.close_channels()
        finally:
            for channel in channels:
                channel.close()


    def search(self, pattern):
        #If backend given that tread as facility, Otherwise search the environment
        import requests
        facility = self.get_backend()
        if not facility:
            facility = os.environ.get("SYSDB_ENV", None)
        api_base_address = "http://iocinfo.psi.ch/api/v2"
        pattern = ".*" + pattern + ".*"  #No regex
        parameters = {"pattern": pattern}
        if facility:
            parameters["facility"] = facility
        parameters["limit"] = 0
        response = requests.get(api_base_address + "/records", params=parameters)
        response.raise_for_status()
        channels = response.json()
        ret = channels
        if not self.verbose:
            pd = self._get_pandas()
            if pd is None:
                if facility:
                    ret = [record["name"] for record in channels]
                else:
                    ret = [f"{record['name']} [{record['facility']}]" for record in channels]
            else:
                ret = None
                header = list(channels[0].keys()) if len(channels) > 0 else []
                data = [d.values() for d in channels]
                df = pd.DataFrame(data, columns=header)
                if (len(header) > 0):
                    df = df.sort_values(by=[header[0], header[1]])
                    columns_to_display = ["facility", "name", "type", "ioc"] #, "description"]
                    ret = df[columns_to_display].to_string(index=False)
        return ret

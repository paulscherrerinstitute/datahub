from datahub import *

_logger = logging.getLogger(__name__)

KNOWN_BACKENDS = ["sf-databuffer", "sf-archiverappliance"]

class DataBuffer(Source):
    """
    Retrieves data from the DataBuffer.
    """

    DEFAULT_URL = os.environ.get("DATA_BUFFER_DEFAULT_URL", "https://data-api.psi.ch/sf-databuffer")
    DEFAULT_BACKEND = os.environ.get("DATA_BUFFER_DEFAULT_BACKEND", "sf-databuffer")

    def __init__(self, url=DEFAULT_URL, backend=DEFAULT_BACKEND, path=None, delay=1.0, **kwargs):
        """
        url (str, optional): DataBuffer URL. Default value can be set by the env var DATA_BUFFER_DEFAULT_URL.
        backend (str, optional): DataBuffer backend. Default value can be set by the env var DATA_BUFFER_DEFAULT_BACKEND.
        path (str, optional): hint for the source location in storage or displaying.
        delay (float, optional): Wait time for channels to be uploaded to storage before retrieval.
        """
        if url is None:
            raise RuntimeError("Invalid URL")
        Source.__init__(self, url=url, backend=backend, query_path="/query",  search_path="/channels", path=path,
                        known_backends=KNOWN_BACKENDS, **kwargs)
        self.delay = delay

    def _get_range(self, start_expansion=False, end_expansion=False):
        type = self.range.end_type
        if type == "id":
            start = self.range.get_start_id()
            end = self.range.get_end_id()
            return {"endPulseId": str(end), "startPulseId": str(start),
                    "startExpansion": start_expansion, "endExpansion": end_expansion}
        elif type == "date":
            start = self.range.get_start_str_iso()
            end = self.range.get_end_str_iso()
            #return {"startDate": datetime.datetime.isoformat(start), "endDate": datetime.datetime.isoformat(end),
            #        "startExpansion": start_expansion, "endExpansion": end_expansion}
            return {"startDate": start, "endDate": end,
                    "startExpansion": start_expansion, "endExpansion": end_expansion}
        elif type == "time":
            start = self.range.get_start_sec()
            end = self.range.get_end_sec()
            return {"startSeconds": "%.9f" % start, "endSeconds": "%.9f" % end,
                    "startExpansion": start_expansion, "endExpansion": end_expansion}
        else:
            raise Exception("Undefined query type")

    def run(self, query):
        import requests
        channels = query.get("channels",[])
        start_expansion = query.get("start_expansion", False)   #Expand query range on start until next datapoint (can be a very expensive operation depending on the backend)
        end_expansion = query.get("end_expansion", False)       # Expand query range on end until next datapoint (can be a very expensive operation depending on the backend
        aggregation = query.get("aggregation", None)
        server_side_mapping = query.get("server_side_mapping", None)
        server_side_mapping_strategy = query.get("server_side_mapping_strategy", "provide-as-is")

        self.range.wait_end(delay=self.delay)

        if isinstance(channels, str):
            channels = [channels, ]
        # Build up channel list for the query
        channel_list = []
        for channel in channels:
            channel_name = channel.split("/")

            if len(channel_name) > 2:
                raise RuntimeError("%s is not a valid channel specification" % channel)
            elif len(channel_name) == 1:
                channel_list.append({"name": channel_name[0]})
            else:
                channel_list.append({"name": channel_name[1], "backend": channel_name[0]})


        query = dict()
        query["channels"] = channel_list
        #query["fields"] = ["pulseId", "globalSeconds", "globalDate", "value", "eventCount"]
        query["fields"] = ["pulseId", "globalSeconds", "globalDate", "value"]

        # Set query ranges
        query["range"] = self._get_range( start_expansion=start_expansion, end_expansion=end_expansion)
        # Set aggregation
        if aggregation is not None:
            query["aggregation"] = aggregation.get_json()

        if server_side_mapping:
            query["mapping"] = {"incomplete": server_side_mapping_strategy}

        response = requests.post(self.url, json=query)

        # Check for successful return of data
        if response.status_code != 200:
            raise RuntimeError("Unable to retrieve data from server: ", response)

        data = response.json()

        for ch in data:
            check_changes=True
            name = ch["channel"]["name"]
            for rec in ch["data"]:
                timestamp = create_timestamp(float(rec["globalSeconds"]))   #rec['eventCount']
                pulse_id = rec["pulseId"]
                value = rec["value"]
                self.receive_channel(name, value, timestamp,pulse_id, check_changes=check_changes, check_types=True)
                check_changes = False
        self.close_channels()

    def search(self, regex):
        import requests
        cfg = {
            "regex": regex,
            "ordering": "asc",
            "reload": "true"
        }
        if self.backend is not None:
            cfg["backends"] = [self.backend]
        response = requests.post(self.search_url, json=cfg)
        ret = response.json()
        if not self.verbose:
            pd = self._get_pandas()
            if pd is None:
                if self.backend and ret[0]['backend'] == self.backend:
                    ret = ret[0]['channels']
            else:
                if len(ret) == 0:
                    return None
                data = []
                for src in ret:
                    for channel in src["channels"]:
                        data.append([src["backend"], channel])
                df = pd.DataFrame(data, columns=["backend", "name"])
                df = df.sort_values(by=["backend", "name"])
                columns_to_display = ["backend", "name"]
                ret = df[columns_to_display].to_string(index=False)
        return ret


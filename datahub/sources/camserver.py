from datahub import *

TIMEOUT = None
_logger = logging.getLogger(__name__)

def validate_response(server_response):
    if server_response["state"] != "ok":
        raise ValueError(server_response.get("status", "Unknown error occurred."))
    return server_response

def get_response(url, post=None, params=None):
    import requests
    if post:
        server_response = requests.post(url, json=None if (post==True) else post, params=params, timeout=TIMEOUT).json()
    else:
        server_response = requests.get(url, params=params, timeout=TIMEOUT).json()
    return validate_response(server_response)


class Pipeline(Bsread):
    DEFAULT_URL = os.environ.get("PIPELINE_DEFAULT_URL", "http://sf-daqsync-01:8889")

    def __init__(self, url=DEFAULT_URL, name=None, config=None, mode="SUB", path=None, **kwargs):
        self.address = url
        if not name and not config:
            raise Exception("Check config")

        if name and name[0] == "_":
            instance = None
            pipeline = name[1:]
        else:
            instance = name
            pipeline = None
        try:
            url = self.get_stream(instance)
        except:
            if not config:
                if pipeline:
                    url = self.create_instance_from_name(name=pipeline, instance_id=instance)
            else:
                if type(config)==str:
                    config = eval(config)
                if pipeline:
                    url = self.create_instance_from_name(name=pipeline, instance_id=instance, additional_config=config)
                else:
                    url = self.create_stream_from_config(config, instance)

        Bsread.__init__(self, url=url, mode=mode, path=path, name=name, **kwargs)

    def get_stream(self, instance_id):
        rest_endpoint = "/api/v1/pipeline/instance/%s" % instance_id
        return get_response(self.address+rest_endpoint)["stream"]

    def create_stream_from_config(self, config, instance_id=None):
        params=None
        if instance_id:
            params = {"instance_id": instance_id} if instance_id else None
            rest_endpoint = "/api/v1/pipeline"
        else:
            rest_endpoint = "/api/v1/pipeline/instance/"
        return get_response(self.address+rest_endpoint, post=config, params=params)["stream"]

    def create_instance_from_name(self, name, instance_id=None, additional_config = None):
        params=None
        rest_endpoint = "/api/v1/pipeline/" + name
        if instance_id or additional_config:
            params = {}
            if instance_id:
                params["instance_id"] = instance_id
            if additional_config:
                #params["additional_config"] = additional_config if type(additional_config) is str else json.dumps(additional_config)
                params["additional_config"] = json.dumps(additional_config)
        return get_response(self.address+rest_endpoint, post=True, params=params)["stream"]


    def get_instances(self):
        rest_endpoint = "/api/v1/pipeline"
        return get_response(self.address+rest_endpoint)["pipelines"]

    def search(self, regex):
        ret = self.get_instances()
        print(ret)
        if regex:
            ret = [element for element in ret if regex in element]
        pd = self._get_pandas()
        if pd:
            if len(ret) == 0:
                return None
            df = pd.DataFrame(ret, columns=["instances"])
            ret = df.to_string(index=False)
        return ret



class Camera(Bsread):
    DEFAULT_URL = os.environ.get("CAMERA_DEFAULT_URL", "http://sf-daqsync-01:8888")

    def __init__(self, url=DEFAULT_URL, name=None, mode="SUB", path=None, **kwargs):
        self.address = url
        if name:
            url = self.get_instance_stream(name)
        Bsread.__init__(self, url=url, mode=mode, path=path, name=name, **kwargs)


    def get_instance_stream(self, instance_id):
        rest_endpoint = "/api/v1/cam/%s" % instance_id
        return get_response(self.address+rest_endpoint)["stream"]

    def get_instances(self):
        rest_endpoint = "/api/v1/cam"
        return get_response(self.address+rest_endpoint)["cameras"]

    def search(self, regex):
        ret = self.get_instances()
        if regex:
            ret = [element for element in ret if regex in element]
        pd = self._get_pandas()
        if pd:
            if len(ret) == 0:
                return None
            df = pd.DataFrame(ret, columns=["instances"])
            ret = df.to_string(index=False)
        return ret

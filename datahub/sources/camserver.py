from datahub import *

TIMEOUT = None

def validate_response(server_response):
    if server_response["state"] != "ok":
        raise ValueError(server_response.get("status", "Unknown error occurred."))
    return server_response

def get_response(url):
    server_response = requests.get(url, timeout=TIMEOUT).json()
    return validate_response(server_response)


class Pipeline(Bsread):
    DEFAULT_URL = os.environ.get("PIPELINE_DEFAULT_URL", "http://sf-daqsync-01:8889")

    def __init__(self, url=DEFAULT_URL, name=None, mode="SUB", path=None, **kwargs):
        self.address = url
        if name:
            url = self.get_instance_stream(name)
        Bsread.__init__(self, url=url, mode=mode, path=path, **kwargs)


    def get_instance_stream(self, instance_id):
        rest_endpoint = "/api/v1/pipeline/instance/%s" % instance_id
        return get_response(self.address+rest_endpoint)["stream"]

    def get_instances(self):
        rest_endpoint = "/api/v1/pipeline"
        return get_response(self.address+rest_endpoint)["pipelines"]

    def search(self, regex):
        instances = self.get_instances()
        if regex:
            instances = [element for element in instances if regex in element]
        return instances




class Camera(Bsread):
    DEFAULT_URL = os.environ.get("CAMERA_DEFAULT_URL", "http://sf-daqsync-01:8888")

    def __init__(self, url=DEFAULT_URL, name=None, mode="SUB", path=None, **kwargs):
        self.address = url
        if name:
            url = self.get_instance_stream(name)
        Bsread.__init__(self, url=url, mode="SUB", path=path, **kwargs)


    def get_instance_stream(self, instance_id):
        rest_endpoint = "/api/v1/cam/%s" % instance_id
        return get_response(self.address+rest_endpoint)["stream"]

    def get_instances(self):
        rest_endpoint = "/api/v1/cam"
        return get_response(self.address+rest_endpoint)["cameras"]

    def search(self, regex):
        instances = self.get_instances()
        if regex:
            instances = [element for element in instances if regex in element]
        return instances

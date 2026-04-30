from datahub import *

_logger = logging.getLogger(__name__)

def validate_response(server_response):
    if server_response["state"] != "ok":
        raise ValueError(server_response.get("status", "Unknown error occurred."))
    return server_response


def get_response(url, post=None, params=None, timeout=None):
    import requests
    if post:
        server_response = requests.post(url, json=None if (post is True) else post, params=params, timeout=timeout).json()
    else:
        server_response = requests.get(url, params=params, timeout=timeout).json()
    return validate_response(server_response)


def split_suffix_in_brackets(s):
    if not s:
        return None, None
    pattern = re.compile(r"(.*)\[(.*)\]$")
    match = pattern.search(s)
    if match:
        # Extract the prefix and the value inside brackets
        prefix = match.group(1)
        value = match.group(2)
        if not prefix:
            prefix=None
        return prefix, value
    else:
        return s, None

class Pipeline(Bsread):
    """
    Retrieves data from CamServer pipelines.
    """
    DEFAULT_URL = os.environ.get("PIPELINE_DEFAULT_URL", "http://sf-daqsync-01:8889")

    def __init__(self, url=DEFAULT_URL, name=None, config=None, mode="SUB", timeout=None, **kwargs):
        """
        url (str, optional): PipelineServer URL. Default value can be set by the env var PIPELINE_DEFAULT_URL.
        name (str, optional): name of the instance and/or pipeline in the format: INSTANCE_NAME[PIPELINE_NAME]
        config (dict, optional): pipeline configuration (or additional configuration if pipeline name is defined)
        mode (str, optional): "SUB" or "PULL"
        timeout (float, optional): server timeout in seconds
        """
        self.address = url
        self.instance, self.pipeline, self.config, self.timeout = None, None, config, timeout
        self.api_prefix = self.address + "/api/v1/pipeline"
        url = None
        if name or config:
            self.instance, self.pipeline = split_suffix_in_brackets(name)
            try:
                url = self.get_stream(self._get_name())
            except:
                if not self.config:
                    if self.pipeline:
                        url = self.create_instance_from_name(name=self.pipeline, instance_id=self.instance)
                else:
                    if type(config) == str:
                        config = eval(config)
                    if self.pipeline:
                        url = self.create_instance_from_name(name=self.pipeline, instance_id=self.instance, additional_config=config)
                    else:
                        url = self.create_stream_from_config(config, self.instance)
                        self.pipeline = config.get("name", None)

        Bsread.__init__(self, url=url, mode=mode, name=name, **kwargs)

    def _get_name(self, instance_id=None):
        if not instance_id:
            instance_id = self.instance
        if not instance_id:
            raise Exception ("Undefined instance name")
        return instance_id

    def _get_pipeline_name(self, pipeline_name=None):
        if not pipeline_name:
            pipeline_name = self.pipeline
            if not pipeline_name:
                pipeline_name = self.get_config().get("name", None)
        if not pipeline_name:
            raise Exception ("Undefined pipeline name")
        return pipeline_name

    def _get_camera_name(self, camera_name=None):
        if not camera_name:
            camera_name = self.get_camera_name()
        if not camera_name:
            raise Exception ("Undefined camera name")
        return camera_name

    def _get_background_name(self, camera_name=None):
        if not camera_name:
            camera_name = self.get_camera_name()
        if not camera_name:
            raise Exception ("Undefined camera name")
        return camera_name

    def _get_response(self, rest_endpoint, post=None, params=None):
        return get_response(self.api_prefix + rest_endpoint, post, params, self.timeout)

    def get_stream(self, instance_id):
        rest_endpoint = "/instance/%s" % instance_id
        return self._get_response(rest_endpoint)["stream"]

    def get_config(self, instance_id=None):
        rest_endpoint = "/instance/%s/config" % self._get_name(instance_id)
        return self._get_response(rest_endpoint)["config"]

    def set_config(self, configuration, instance_id=None):
        rest_endpoint = "/instance/%s/config" % self._get_name(instance_id)
        return self._get_response(rest_endpoint, post=configuration)["config"]

    def set_config_item(self, name, value, instance_id=None):
        cfg = self.get_config(instance_id)
        cfg[name] = value
        return self.set_config(cfg, instance_id)

    def get_saved_config(self, pipeline_name=None):
        rest_endpoint = "/%s/config" % self._get_pipeline_name(pipeline_name)
        return self._get_response(rest_endpoint)["config"]

    def set_saved_config(self, configuration, pipeline_name=None):
        rest_endpoint = "/%s/config" % self._get_pipeline_name(pipeline_name)
        return self._get_response(rest_endpoint, post=configuration)["config"]

    def set_saved_config_item(self, name, value, pipeline_name=None):
        cfg = self.get_saved_config(pipeline_name)
        cfg[name] = value
        return self.set_saved_config(cfg, pipeline_name)

    def get_camera_name(self):
        cfg = self.get_config()
        return cfg.get("camera_name", None)

    def get_background_name(self):
        cfg = self.get_config()
        if cfg.get("image_background_enable", False):
            return cfg.get("image_background", None)
        return None

    def get_latest_background(self, camera_name=None):
        rest_endpoint = "/camera/%s/background" % self._get_camera_name(camera_name)
        return self._get_response(rest_endpoint)["background_id"]

    def get_backgrounds(self, camera_name=None):
        rest_endpoint = "/camera/%s/backgrounds" % self._get_camera_name(camera_name)
        return self._get_response(rest_endpoint)["background_ids"]

    def get_background(self, background_name=None):
        import base64
        if background_name is None:
            background_name = self.get_background_name()

        rest_endpoint = "/background/%s/image_bytes" % background_name
        image = self._get_response(rest_endpoint)["image"]
        dtype = image["dtype"]
        shape = image["shape"]
        bytes = base64.b64decode(image["bytes"].encode())
        return numpy.frombuffer(bytes, dtype=dtype).reshape(shape)

    def create_stream_from_config(self, config, instance_id=None):
        params=None
        if instance_id:
            params = {"instance_id": instance_id} if instance_id else None
            rest_endpoint = ""
        else:
            rest_endpoint = "/instance/"
        return self._get_response(rest_endpoint, post=config, params=params)["stream"]

    def create_instance_from_name(self, name, instance_id=None, additional_config = None):
        params=None
        rest_endpoint = "/" + name
        if instance_id or additional_config:
            params = {}
            if instance_id:
                params["instance_id"] = instance_id
            if additional_config:
                #params["additional_config"] = additional_config if type(additional_config) is str else json.dumps(additional_config)
                params["additional_config"] = json.dumps(additional_config)
        return self._get_response(rest_endpoint, post=True, params=params)["stream"]

    def get_pipelines(self):
        rest_endpoint = ""
        return self._get_response(rest_endpoint)["pipelines"]

    def get_instances(self):
        return list(self.get_info()["active_instances"].keys())

    def get_info(self):
        rest_endpoint = "/info"
        return self._get_response(rest_endpoint)["info"]

    def get_groups(self):
        rest_endpoint = "/groups"
        return self._get_response(rest_endpoint)["groups"]


    def search(self, regex, case_sensitive=True):
        ret = self.get_instances()
        if regex:
            if case_sensitive:
                ret = [element for element in ret if regex in element]
            else:
                ret = [element for element in ret if regex.lower() in element.lower()]
        pd = self._get_pandas()
        if pd:
            if len(ret) == 0:
                return None
            df = pd.DataFrame(ret, columns=["instances"])
            ret = df.to_string(index=False)
        return ret

class Camera(Bsread):
    """
    Retrieves data from CamServer cameras.
    """
    DEFAULT_URL = os.environ.get("CAMERA_DEFAULT_URL", "http://sf-daqsync-01:8888")

    def __init__(self, url=DEFAULT_URL, name=None, mode="SUB", timeout=None, **kwargs):
        """
        url (str, optional): CameraServer URL. Default value can be set by the env var CAMERA_DEFAULT_URL.
        name (str): camera name
        mode (str, optional): "SUB" or "PULL"
        timeout (float, optional): server timeout in seconds
        """
        self.address = url
        self.timeout = timeout
        self.name = name
        self.api_prefix = self.address + "/api/v1/cam"
        url = self.get_stream(name) if name else None
        Bsread.__init__(self, url=url, mode=mode, name=name, **kwargs)

    def _get_name(self, name=None):
        if not name:
            name = self.name
        if not name:
            raise Exception ("Undefined camera name")
        return name

    def _get_response(self, rest_endpoint, post=None, params=None):
        return get_response(self.api_prefix + rest_endpoint, post, params, self.timeout)

    def get_stream(self, name):
        rest_endpoint = "/%s" % name
        return self._get_response(rest_endpoint)["stream"]

    def is_camera_online(self, name=None):
        rest_endpoint = "/%s/is_online" % self._get_name(name)
        return self._get_response(rest_endpoint)["online"]

    def get_config(self, name=None):
        rest_endpoint = "/%s/config" % self._get_name(name)
        return self._get_response(rest_endpoint)["config"]

    def get_cameras(self):
        rest_endpoint = ""
        return self._get_response(rest_endpoint)["cameras"]

    def get_instances(self):
        return list(self.get_info()["active_instances"].keys())

    def get_info(self):
        rest_endpoint = "/info"
        return self._get_response(rest_endpoint)["info"]

    def get_groups(self):
        rest_endpoint = "/groups"
        return self._get_response(rest_endpoint)["groups"]

    def get_aliases(self):
        rest_endpoint = "/aliases"
        return self._get_response(rest_endpoint)["aliases"]

    def search(self, regex, case_sensitive=True):
        ret = self.get_instances()
        if regex:
            if case_sensitive:
                ret = [element for element in ret if regex in element]
            else:
                ret = [element for element in ret if regex.lower() in element.lower()]
        pd = self._get_pandas()
        if pd:
            if len(ret) == 0:
                return None
            df = pd.DataFrame(ret, columns=["instances"])
            ret = df.to_string(index=False)
        return ret




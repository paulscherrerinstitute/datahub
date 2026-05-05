from datahub import *

_logger = logging.getLogger(__name__)

class CamServerClient(Bsread):
    def __init__(self, api_prefix, name=None, config=None, mode="SUB", timeout=None, **kwargs):
        self.api_prefix = api_prefix
        self.timeout = timeout
        self.name = name
        self.config = eval(config) if type(config) == str else config
        Bsread.__init__(self, url=self._get_stream(), mode=mode, name=name, **kwargs)

    def _get_name(self, name=None):
        name = name or self.name
        if not name:
            raise ValueError ("Undefined instance name")
        return name

    def _get_config_name(self, config_name=None):
        return self._get_name(config_name)

    def get_response(self, endpoint, post=None, params=None, delete=False):
        return get_response(url=self.api_prefix+endpoint, post=post, params=params, delete=delete, timeout=self.timeout)

    def get_info(self):
        return self.get_response("/info")["info"]

    def stop_instance(self, id=None):
        self.get_response("/%s" % self._get_name(id), delete=True)

    def get_instances(self):
        return list(self.get_info()["active_instances"].keys())

    def is_active(self, name=None):
        return self._get_name(name) in self.get_instances()

    def get_config(self, name=None):
        return self.get_response("/%s/config" % self._get_config_name(name))["config"]

    def set_config(self, configuration, name=None):
        return self.get_response("/%s/config" % self._get_config_name(name), post=configuration)["config"]

    def set_config_item(self, item, value, name=None):
        cfg = self.get_config(name)
        cfg[item] = value
        return self.set_config(cfg, name)

    def get_config_names(self):
        #return self.get_response("/config_names")["config_names"] #Failing in CameraServer
        return self.get_response("")["cameras" if type(self) is Camera else "pipelines"]

    def get_groups(self):
        return self.get_response("/groups")["groups"]

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

class Camera(CamServerClient):
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
        CamServerClient.__init__(self, api_prefix=url + "/api/v1/cam", name=name, mode=mode, timeout=timeout, **kwargs)

    def _get_stream(self):
        return self.get_response("/%s" % self.name)["stream"] if self.name else None

    def is_online(self, name=None):
        return self.get_response("/%s/is_online" % self._get_name(name))["online"]

    def get_aliases(self):
        return self.get_response("/aliases")["aliases"]

class Pipeline(CamServerClient):
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
        #Split name INSTANCE[PIPELINE]
        self.pipeline = None
        if name:
            pattern = re.compile(r"(.*)\[(.*)\]$")
            match = pattern.search(name)
            if match:
                name, self.pipeline = match.group(1), match.group(2)
        CamServerClient.__init__(self, api_prefix=url+"/api/v1/pipeline", name=name if name else None, config=config, mode=mode, timeout=timeout, **kwargs)

    def _get_stream(self):
        if self.name or self.config:
            try:
                return self._get_active_stream(self._get_name())
            except:
                if self.config:
                    if self.pipeline:
                        return self._create_stream_from_name(name=self.pipeline, instance_id=self.name, additional_config=self.config)
                    else:
                        self.pipeline = self.config.get("name", None)
                        return self._create_stream_from_config(self.config, self.name)

                else:
                    if self.pipeline:
                        return self._create_stream_from_name(name=self.pipeline, instance_id=self.name)

    def _get_active_stream(self, instance_id):
        return self.get_response("/instance/%s" % instance_id)["stream"]

    def _create_stream_from_config(self, config, instance_id=None):
        if instance_id:
            return self.get_response("", post=config, params={"instance_id": instance_id} if instance_id else None)["stream"]
        else:
            return self.get_response("/instance/", post=config)["stream"]

    def _create_stream_from_name(self, name, instance_id=None, additional_config=None):
        params = {}
        if instance_id or additional_config:
            if instance_id:
                params["instance_id"] = instance_id
            if additional_config:
                params["additional_config"] = json.dumps(additional_config)
        return self.get_response("/" + name, post=True, params=params if params else None)["stream"]

    def _get_config_name(self, pipeline_name=None):
        pipeline_name = pipeline_name or self.pipeline or self.get_instance_config().get("name", None)
        if not pipeline_name:
            raise ValueError("Undefined pipeline name")
        return pipeline_name

    def _get_camera_name(self, camera_name=None):
        camera_name = camera_name or self.get_camera_name()
        if not camera_name:
            raise ValueError("Undefined camera name")
        return camera_name

    def get_instance_config(self, instance_id=None):
        return self.get_response("/instance/%s/config" % self._get_name(instance_id))["config"]

    def set_instance_config(self, configuration, instance_id=None):
        return self.get_response( "/instance/%s/config" % self._get_name(instance_id), post=configuration)["config"]

    def set_instance_config_item(self, name, value, instance_id=None):
        cfg = self.get_instance_config(instance_id)
        cfg[name] = value
        return self.set_instance_config(cfg, instance_id)

    def get_camera_name(self, instance_id=None):
        return self.get_instance_config(instance_id).get("camera_name", None)

    def get_background_name(self, instance_id=None):
        cfg = self.get_instance_config(instance_id)
        if cfg.get("image_background_enable", False):
            return cfg.get("image_background", None)
        return None

    def get_latest_background(self, camera_name=None):
        return self.get_response("/camera/%s/background" % self._get_camera_name(camera_name))["background_id"]

    def get_backgrounds(self, camera_name=None):
        return self.get_response( "/camera/%s/backgrounds" % self._get_camera_name(camera_name))["background_ids"]

    def get_background(self, background_name=None):
        import base64
        background_name = background_name or self.get_background_name()
        image = self.get_response( "/background/%s/image_bytes" % background_name)["image"]
        dtype, shape, bytes = image["dtype"], image["shape"], base64.b64decode(image["bytes"].encode())
        return numpy.frombuffer(bytes, dtype=dtype).reshape(shape)

    def collect_background(self, camera_name=None, n_images=None):
        return self.get_response("/camera/%s/background" % self._get_camera_name(camera_name), post=True,
                                 params= {"n_images": n_images} if n_images else None)["background_id"]

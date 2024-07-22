from datahub import *
try:
    import redis
except:
    redis = None

class Stddaq(Bsread):
    """
    Retrieves data from CamServer cameras.
    """
    DEFAULT_URL = os.environ.get("STDDAQ_DEFAULT_URL", "sf-daq-6.psi.ch:6379")

    def __init__(self, url=DEFAULT_URL, name=None, mode="SUB", path=None, **kwargs):
        """
        url (str, optional): URL for Stddaq Redis repo.
        name (str): device name
        mode (str, optional): "SUB" or "PULL"
        path (str, optional): hint for the source location in storage or displaying.
        """
        self.address = url
        if redis is None:
            raise Exception("PyRedis library not available")
        self.host, self.port = get_host_port_from_stream_address(url)
        self.db='0'
        if name:
            url = self.get_instance_stream(name)
        Bsread.__init__(self, url=url, mode=mode, path=path, name=name, **kwargs)

    def get_instance_stream(self, name):
        with redis.Redis(host=self.host, port=self.port, db=self.db) as r:
            ret = r.get(name)
            return ret.decode('utf-8').strip()   if ret else ret


    def search(self, regex):
        with redis.Redis(host=self.host, port=self.port, db=self.db) as r:
            if not regex:
                #return r.config_get('databases')
                return r.info('keyspace')
            else:
                cursor = '0'
                streams = []
                match = f'*{regex}*' if regex else '*'
                while cursor != 0:
                    cursor, keys = r.scan(cursor=cursor, match=match)
                    for key in keys:
                        if r.type(key) == b'string':
                            if type(key) != str:
                                key = key.decode('utf-8')
                            streams.append(key)
                return sorted(streams)

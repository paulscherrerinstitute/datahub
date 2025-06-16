
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

    def __init__(self, url=DEFAULT_URL, name=None, replay=False, **kwargs):
        """
        url (str, optional): URL for Stddaq Redis repo.
        name (str): device name
        replay (str, optional): If True data is retrieved from the buffer (PULL).
                                If False data is live streamed (SUB).
        """
        if redis is None:
            raise Exception("Redis library not available")
        self.host, self.port = get_host_port_from_stream_address(url)
        self.address = url
        self.name = name
        self.replay = replay
        self.db = '0'
        mode = "PULL" if replay else "SUB"
        if name:
            name = "REPLAY-" + self.name if replay else self.name
            url = self.get_instance_stream(name)
        Bsread.__init__(self, url=url, mode=mode, name=self.name, **kwargs)

    def get_instance_stream(self, name):
        with redis.Redis(host=self.host, port=self.port, db=self.db) as r:
            ret = r.get(name)
            return ret.decode('utf-8').strip() if ret else ret

    def run(self, query):
        if self.replay:
            #Start query
            pass
        Bsread.run(self, query=query)

    def search(self, regex=None, case_sensitive=True):
        redis_source = datahub.Redis(url=self.address, backend=self.db)
        return redis_source.search(regex, case_sensitive)
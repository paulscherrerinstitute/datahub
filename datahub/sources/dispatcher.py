from datahub.sources.bsread import Bsread, bsread

class Dispatcher(Bsread):
    DEFAULT_URL = bsread.DEFAULT_DISPATCHER_URL

    def __init__(self, url=DEFAULT_URL, path=None, **kwargs):
        Bsread.__init__(self, url=url, mode="SUB", path=path, **kwargs)

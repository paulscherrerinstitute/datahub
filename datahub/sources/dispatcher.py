from datahub.sources.bsread import Bsread

class Dispatcher(Bsread):

    def __init__(self, path=None, **kwargs):
        Bsread.__init__(self, url=None, mode="SUB", path=path, **kwargs)

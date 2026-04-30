import os
from datahub.sources.bsread import Bsread, bsread

class Dispatcher(Bsread):
    """
    Retrieves data from the DataBuffer dispatcher.
    """
    DEFAULT_URL = os.environ.get("DISPATCHER_DEFAULT_URL", None if (bsread is None) else bsread.DEFAULT_DISPATCHER_URL)

    def __init__(self, url=DEFAULT_URL, **kwargs):
        """
        """
        #Parameter dispatcher_url of bsread.source is not working
        if url and (url != bsread.DEFAULT_DISPATCHER_URL):
            bsread.DEFAULT_DISPATCHER_URL = url
        Bsread.__init__(self, url=None, mode="SUB", **kwargs)

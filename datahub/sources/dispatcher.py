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
        Bsread.__init__(self, url=None, mode="SUB", dispatcher_url=url, **kwargs)

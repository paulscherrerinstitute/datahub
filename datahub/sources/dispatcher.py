from datahub.sources.bsread import Bsread

class Dispatcher(Bsread):
    """
    Retrieves data from the DataBuffer dispatcher.
    """

    def __init__(self, **kwargs):
        """
        """
        Bsread.__init__(self, url=None, mode="SUB", **kwargs)

from datahub.sources.bsread import Bsread

class Dispatcher(Bsread):
    """
    Retrieves data from the DataBuffer dispatcher.
    """

    def __init__(self, path=None, **kwargs):
        """
        path (str, optional): hint for the source location in storage or displaying.
        """
        Bsread.__init__(self, url=None, mode="SUB", path=path, **kwargs)

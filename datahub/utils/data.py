import secrets
import string
import collections
import pickle

class MaxLenDict(collections.OrderedDict):
    def __init__(self, *args, **kwds):
        self.maxlen = kwds.pop("maxlen", None)
        collections.OrderedDict.__init__(self, *args, **kwds)
        self._check_maxlen()

    def __setitem__(self, key, value):
        collections.OrderedDict.__setitem__(self, key, value)
        self._check_maxlen()

    def _check_maxlen(self):
        if self.maxlen is not None:
            while len(self) > self.maxlen:
                self.popitem(last=False)


def generate_random_string(length=16):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


def decode(data):
    obj = pickle.loads(data)
    return obj

def encode(obj):
    value_serialized = pickle.dumps(obj)
    return value_serialized
import secrets
import string
import collections
#import pickle
try:
    import cbor2
except:
    cbor2 = None
import numpy as np

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
    #return pickle.loads(data)
    if cbor2 is None:
        raise Exception("cbor2 library not available")
    obj = cbor2.loads(data)
    if type(obj)!=dict:
        return None
    data = obj.get("data")
    shape = obj.get("shape", None)
    dtype = obj.get("dtype", None)
    if shape is not None:
        data = np.frombuffer(data, dtype=np.dtype(dtype))
        data = data.reshape(shape)
    return data

def encode(obj):
    if cbor2 is None:
        raise Exception("cbor2 library not available")
    #return pickle.dumps(obj)
    if type(obj) == np.ndarray:
        obj = {
            'shape': obj.shape,
            'dtype': str(obj.dtype),
            'data': obj.tobytes()
        }
    else:
        obj = {"data": obj}
    ret = cbor2.dumps(obj)
    return ret
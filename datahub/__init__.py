from pkg_resources import resource_stream
import os

def version():
    with resource_stream(__name__, "package_version.txt") as res:
        return res.read()[:-1].decode()

def str_to_bool(str):
    if str.lower() in ('true', 'yes', '1'):
        return True
    if str.lower() in ('false', 'no', '0'):
        return False
    return None

def is_null_str(str):
    return (str is None) or (str.lower() == "null") or (str.lower() == "none")

class ProtocolError(RuntimeError):
    def __init__(self):
        super().__init__("ProtocolError")

from datahub.utils.timing import *
from datahub.utils.net import *
from datahub.utils.compression import *
from datahub.utils.range import QueryRange
from datahub.source import Source
from datahub.sources.retrieval import Retrieval
from datahub.sources.bsread import Bsread, BsreadStream
from datahub.sources.array10 import Array10
from datahub.sources.epics import Epics
from datahub.sources.camserver import Pipeline
from datahub.sources.camserver import Camera
from datahub.sources.databuffer import DataBuffer
from datahub.sources.dispatcher import Dispatcher
from datahub.sources.daqbuf import Daqbuf
from datahub.sources.stddaq import Stddaq
from datahub.sources.redis import Redis, RedisStream
from datahub.consumer import Consumer
from datahub.consumers.h5 import HDF5Writer
from datahub.consumers.txt import TextWriter
from datahub.consumers.stdout import Stdout
from datahub.consumers.table import Table
from datahub.consumers.pshell import PShell
from datahub.consumers.plot import Plot
from datahub.consumers.merger import Merger

def cleanup():
    Source.cleanup()
    Consumer.cleanup()

KNOWN_CONSUMERS = {
    "hdf5": ("f", HDF5Writer),
    "txt":  ("x", TextWriter),
    "print": ("p", Stdout),
    "plot": ("m", Plot),
    "pshell": ("ps", PShell)
}

KNOWN_SOURCES = {
    "epics": Epics,
    "bsread": Bsread,
    "pipeline": Pipeline,
    "camera": Camera,
    "databuffer": DataBuffer,
    "retrieval": Retrieval,
    "dispatcher": Dispatcher,
    "daqbuf": Daqbuf,
    "array10": Array10,
    "redis": Redis,
    "stddaq": Stddaq
    }

DEFAULT_SOURCE = os.environ.get("DEFAULT_DATA_SOURCE", "daqbuf")
#from datahub.main import run_json

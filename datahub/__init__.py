from pkg_resources import resource_stream

def version():
    with resource_stream(__name__, "package_version.txt") as res:
        return res.read()[:-1].decode()


class ProtocolError(RuntimeError):
    def __init__(self):
        super().__init__("ProtocolError")

from datahub.utils.timing import *
from datahub.utils.net import *
from datahub.utils.compression import *
from datahub.utils.range import QueryRange
from datahub.source import Source
from datahub.sources.retrieval import Retrieval
from datahub.sources.bsread import Bsread
from datahub.sources.epics import Epics
from datahub.sources.camserver import Pipeline
from datahub.sources.camserver import Camera
from datahub.sources.databuffer import DataBuffer
from datahub.sources.dispatcher import Dispatcher
from datahub.consumer import Consumer
from datahub.consumers.h5 import HDF5Writer
from datahub.consumers.txt import TextWriter
from datahub.consumers.stdout import StdoutWriter
from datahub.consumers.table import Table

def cleanup():
    Source.cleanup()
    Consumer.cleanup()


KNOWN_SOURCES  = {
    "epics":Epics,
    "bsread":Bsread,
    "pipeline":Pipeline,
    "camera":Camera,
    "databuffer":DataBuffer,
    "retrieval":Retrieval,
    "dispatcher":Dispatcher
    }
from datahub.main import run_json

import sys
import time

start = time.time()
import os,time,logging,dateutil,json,ssl,urllib,re,numpy,struct,bitshuffle
from pkg_resources import resource_stream
print  (time.time() - start)


start = time.time()
from datahub import *
print  (time.time() - start)



start = time.time()
DEFAULT_SOURCE = os.environ.get("DEFAULT_DATA_SOURCE", "daqbuf")
from datahub.main import run_json
print  (time.time() - start)

# Function to get the top-level modules imported by the application
def get_imported_modules():
    return [name for name, obj in globals().items() if isinstance(obj, type(sys))]

# Print the names of imported modules
imported_modules = get_imported_modules()
print("Imported Modules:", imported_modules)
# Overview

This package provides utilities to retrieve data from PSI sources.


# Installation

Install via Anaconda/Miniconda:

```
conda install -c paulscherrerinstitute -c conda-forge  datahub
```

# Usage from command line

On the command line data can be retrieved as follow:

```bash
datahub --file <FILE_NAME> --start <START> --end <END> --<SERVICE> <option_1> <value_1> ... <option_n> <value_n> 
```

This is the help message for the 'datahub' command: 
```
$ datahub  -h                                                                                                                                                                           
usage: main.py [-h] [-j JSON] [-f FILE] [-t FILE] [-p] [-s START] [-e END] [-c COMPRESSION] [-d] [-l LOCATION] [-r [SEARCH ...]] [--epics [channels url=None path=None start=None end=None ...]]
               [--bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None ...]] [--pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None ...]]
               [--camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None ...]] [--databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None start=None end=None ...]]
               [--retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None start=None end=None ...]] [--dispatcher [channels url='https://dispatcher-api.psi.ch/sf-databuffer' path=None start=None end=None ...]]

Command line interface for DataHub 1.0.0

optional arguments:
  -h, --help            show this help message and exit
  -j JSON, --json JSON  Complete query defined as JSON
  -f FILE, --file FILE  Save data to file
  -t FILE, --format FILE
                        File format (Default hdf5)
  -p, --print           Print data to stdout
  -s START, --start START
                        Relative or absolute start time (or ID)
  -e END, --end END     Relative or absolute end time (or ID)
  -c COMPRESSION, --compression COMPRESSION
                        Compression (Default gzip)
  -d, --decompress      Auto-decompress compressed images
  -l LOCATION, --location LOCATION
                        Path to data
  -r [SEARCH ...], --search [SEARCH ...]
                        Search channel names given by regex instead of fetching data
  --epics [channels url=None path=None start=None end=None ...]
                        epics query arguments
  --bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None ...]
                        bsread query arguments
  --pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None ...]
                        pipeline query arguments
  --camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None ...]
                        camera query arguments
  --databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None start=None end=None ...]
                        databuffer query arguments
  --retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None start=None end=None ...]
                        retrieval query arguments
  --dispatcher [channels url='https://dispatcher-api.psi.ch/sf-databuffer' path=None start=None end=None ...]
                        dispatcher query arguments



# Usage from commandline with /api/1 service

This newer service is currently in testing.

```bash
api3 --baseurl https://data-api.psi.ch/api/1 --default-backend sf-databuffer save output.h5 2020-10-08T19:30:00.123Z 2020-10-08T19:33:00.789Z SINLH01-DBAM010:EOM1_T1
```


# Usage as library

## sf-databuffer with time range

```python
from datahub import *

query = {
    "channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
    "start": "2024-02-14 08:50:00.000",
    "end": "2024-02-14 08:50:05.000"
}

with DataBuffer(backend="sf-databuffer") as source:
    stdout = Stdout()
    table = Table()
    source.add_listener(table)
    source.request(query)
    dataframe = table.as_dataframe()
    print(dataframe)
```

## sf-imagebuffer with pulse id range

```python
from datahub import *

query = {
    "channels": ["SLG-LCAM-C081:FPICTURE"],
    "start": 20337230810,
    "end": 20337231300
}

with Retrieval(url="http://sf-daq-5.psi.ch:8380/api/1", backend="sf-imagebuffer") as source:
    stdout = Stdout()
    table = Table()
    source.add_listener(table)
    source.request(query)
    print(table.data["SLG-LCAM-C081:FPICTURE"])
```



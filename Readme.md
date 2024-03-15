# Overview

This package provides utilities to retrieve data from PSI sources.

# Sources

These are the supported data sources: 
- daqbuf (default)
- epics
- databuffer
- retrieval
- dispatcher
- pipeline
- camera
- bsread
- array10

# Consumers

These are the available data consumers: 
- hdf5: save receive data in a single hdf5 file.  
- txt: save received data in text files.
- print: prints data to stdout.
- plot: plots data to Matplotlib graphs.
- pshell: sends data to a PShell plot server.


# Installation

Install via Anaconda/Miniconda:

```
conda install -c paulscherrerinstitute -c conda-forge  datahub
```

# Usage from command line

On the command line data can be retrieved as follow:

```bash
datahub --file <FILE_NAME> --start <START> --end <END> --<SOURCE> <option_1> <value_1> ... <option_n> <value_n> 
```


This is the help message for the 'datahub' command: 
```
$ datahub  -h                                                                                                                                                                           
usage: main.py [-h] [-j JSON] [-f [filename default_compression='gzip' auto_decompress=False path=None metadata_compression='gzip'  ...]] [-x [folder  ...]] [-p [...]] [-m [channels=None colormap='viridis' color=None marker_size=None line_width=None max_count=None max_rate=None  ...]]
               [-ps [channels=None address='localhost' port=7777 timeout=3.0 layout='vertical' context=None style=None colormap='viridis' color=None marker_size=3 line_width=None max_count=None max_rate=None  ...]] [-v] [-s START] [-e END] [-i] [-t] [-c CHANNELS] [-u URL] [-b BACKEND]
               [-tt TIMESTAMP] [-cp COMPRESSION] [-dc] [-pl] [-px] [-pt PATH] [-sr [SEARCH ...]] [-di INTERVAL] [-dm MODULO] [--epics [channels url=None path=None start=None end=None ...]]
               [--bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None ...]] [--pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None ...]]
               [--camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None ...]] [--databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None delay=1.0 start=None end=None ...]]
               [--retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None delay=1.0 start=None end=None ...]] [--dispatcher [channels url='https://dispatcher-api.psi.ch/sf-databuffer' path=None start=None end=None ...]]
               [--daqbuf [channels url='https://data-api.psi.ch/api/4' backend='sf-databuffer' path=None delay=1.0 cbor=True parallel=False start=None end=None ...]] [--array10 [channels url=None mode='SUB' path=None reshape=False start=None end=None ...]]

Command line interface for DataHub 1.0.0

optional arguments:
  -h, --help            show this help message and exit
  -j, --json JSON       Complete query defined as JSON
  -f, --hdf5 [filename default_compression='gzip' auto_decompress=False path=None metadata_compression='gzip'  ...]
                        hdf5 options
  -x, --txt [folder  ...]
                        txt options
  -p, --print [ ...]    print options
  -m, --plot [channels=None colormap='viridis' color=None marker_size=None line_width=None max_count=None max_rate=None  ...]
                        plot options
  -ps, --pshell [channels=None address='localhost' port=7777 timeout=3.0 layout='vertical' context=None style=None colormap='viridis' color=None marker_size=3 line_width=None max_count=None max_rate=None  ...]
                        pshell options
  -v, --verbose         Displays complete search results, not just channels names
  -s, --start START     Relative or absolute start time or ID
  -e, --end END         Relative or absolute end time or ID
  -i, --id              Force query by id
  -t, --time            Force query by time
  -c, --channels CHANNELS
                        Channel list (comma-separated)
  -u, --url URL         URL of default source
  -b, --backend BACKEND
                        Backend of default source
  -tt, --timestamp TIMESTAMP
                        Timestamp type: nano/int (default), sec/float or str
  -cp, --compression COMPRESSION
                        Compression: gzip (default), szip, lzf, lz4 or none
  -dc, --decompress     Auto-decompress compressed images
  -pl, --parallel       Parallelize query if possible
  -px, --prefix         Add source ID to channel names
  -pt, --path PATH      Path to data in the file
  -sr, --search [SEARCH ...]
                        Search channel names given a pattern (instead of fetching data)
  -di, --interval INTERVAL
                        Downsampling interval between samples in seconds
  -dm, --modulo MODULO  Downsampling modulo of the samples
  --epics [channels url=None path=None start=None end=None ...]
                        epics query arguments
  --bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None ...]
                        bsread query arguments
  --pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None ...]
                        pipeline query arguments
  --camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None ...]
                        camera query arguments
  --databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None delay=1.0 start=None end=None ...]
                        databuffer query arguments
  --retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None delay=1.0 start=None end=None ...]
                        retrieval query arguments
  --dispatcher [channels url='https://dispatcher-api.psi.ch/sf-databuffer' path=None start=None end=None ...]
                        dispatcher query arguments
  --daqbuf [channels url='https://data-api.psi.ch/api/4' backend='sf-databuffer' path=None delay=1.0 cbor=True parallel=False start=None end=None ...]
                        daqbuf query arguments
  --array10 [channels url=None mode='SUB' path=None reshape=False start=None end=None ...]
                        array10 query arguments
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



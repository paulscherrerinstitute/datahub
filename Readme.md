# Overview

This package provides utilities to retrieve data from PSI sources.

# Installation

Install via Anaconda/Miniconda:

```
conda install -c paulscherrerinstitute -c conda-forge  datahub
```

# Sources

Sources are services that provide data.

There are 2 kinds of sources:
- Streaming: can only retrieve data in the future.
- Retrieving: can only retrieve data from the past (must wait when requesting future data).

Despite the different natures of these two kinds, datahub has a common way for defining ranges. 

These are the currently supported data sources: 

- daqbuf - aka 'new retrieval' (default) 
- epics
- databuffer
- retrieval
- dispatcher
- pipeline
- camera
- bsread
- array10

# Consumers

Consumers receive and process data streams from sources. 
These are the available data consumers:
 
- hdf5: save receive data in hdf5 file.   
  Argument: file name
- txt: save received data in text files.   
  Argument: folder name
- print: prints data to stdout.
- plot: plots data to Matplotlib graphs.   
  Optional plot arguments:
  - channels=None  (plot subset of the available channels)
  - colormap="viridis"
  - color=None
  - marker_size=None
  - line_width=None
  - max_count=None
  - max_rate=None 
- pshell: sends data to a PShell plot server.   
  Optional plot arguments:
  - channels=None
  - address="localhost"
  - port=7777
  - timeout=3.0
  - layout="vertical"
  - context=None,
  - style=None
  - colormap="viridis"
  - color=None
  - marker_size=3
  - line_width=None
  - max_count=None
  - max_rate=None 



# Usage from command line

On the command line, datahub commands use the following pattern:

- datahub [GLOBAL ARGUMENTS] [--<SOURCE NAME 1> [SOURCE ARGUMENTS]]> ... [--<SOURCE NAME n> [SOURCE ARGUMENTS]]

Example:

```bash
datahub --file <FILE_NAME> --start <START> --end <END> --<SOURCE_1> <option_1> <value_1> ... <option_n> <value_n> ... --<SOURCE_n> <option_1> <value_1> ... <option_m> <value_m> 
```


- If no source is specified then __daqbuf__ source is assumed:
```bash
datahub --print --hdf5 ~/.data.h5  --start "2024-02-14 08:50:00.000" --end "2024-02-14 08:50:10.000" --channels S10BC01-DBPM010:Q1,S10BC01-DBPM010:X1 
```

- A single run can retrieve data simultaneously from multiple sources.
```bash
datahub -p --epics s 0.0 e 2.0 c S10BC01-DBPM010:X1 --daqbuf s 0.0 e 2.0 c S10BC01-DBPM010:Q1 delay 30.0 
```

The example above saves the next 2 seconds of data from an EPICS channel, and also from databuffer data read through daqbuf.
Being daqbuf a retrieving source, and given the fact we want future data, a "delay" parameter is specified to provide the time needed
for actual data to be available in daqbuf backend.


The argument documentation is available in the help message for the 'datahub' command: 
```
usage: main.py [-h] [-j JSON] [-f [filename default_compression='gzip' auto_decompress=False path=None metadata_compression='gzip']] [-x [folder]] [-p]
               [-m [channels=None colormap='viridis' color=None marker_size=None line_width=None max_count=None max_rate=None]]
               [-ps [channels=None address='localhost' port=7777 timeout=3.0 layout='vertical' context=None style=None colormap='viridis' color=None marker_size=3 line_width=None max_count=None max_rate=None]]
               [-v] [-s START] [-e END] [-i] [-t] [-c CHANNELS] [-u URL] [-b BACKEND] [-tt TIMESTAMP] [-cp COMPRESSION] [-dc] [-pl] [-px] [-pt PATH] [-sr] [-di INTERVAL]
               [-dm MODULO] [--epics [channels url=None path=None start=None end=None]]
               [--bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None]]
               [--pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None]]
               [--camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None]]
               [--databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None delay=1.0 start=None end=None]]
               [--retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None delay=1.0 start=None end=None]]
               [--dispatcher [channels path=None start=None end=None]]
               [--daqbuf [channels url='https://data-api.psi.ch/api/4' backend='sf-databuffer' path=None delay=1.0 cbor=True parallel=False start=None end=None]]
               [--array10 [channels url=None mode='SUB' path=None reshape=False start=None end=None]]

Command line interface for DataHub 1.0.0

optional arguments:
  -h, --help            show this help message and exit
  -j, --json JSON       Complete query defined as JSON
  -f, --hdf5 [filename default_compression='gzip' auto_decompress=False path=None metadata_compression='gzip' ]
                        hdf5 options
  -x, --txt [folder ]   txt options
  -p, --print           print options
  -m, --plot [channels=None colormap='viridis' color=None marker_size=None line_width=None max_count=None max_rate=None ]
                        plot options
  -ps, --pshell [channels=None address='localhost' port=7777 timeout=3.0 layout='vertical' context=None style=None colormap='viridis' color=None marker_size=3 line_width=None max_count=None max_rate=None ]
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
  -sr, --search         Search channel names given a pattern (instead of fetching data)
  -di, --interval INTERVAL
                        Downsampling interval between samples in seconds
  -dm, --modulo MODULO  Downsampling modulo of the samples
  --epics [channels url=None path=None start=None end=None]
                        epics query arguments
  --bsread [channels url='https://dispatcher-api.psi.ch/sf-databuffer' mode='SUB' path=None start=None end=None]
                        bsread query arguments
  --pipeline [channels url='http://sf-daqsync-01:8889' name=None mode='SUB' path=None start=None end=None]
                        pipeline query arguments
  --camera [channels url='http://sf-daqsync-01:8888' name=None mode='SUB' path=None start=None end=None]
                        camera query arguments
  --databuffer [channels url='https://data-api.psi.ch/sf-databuffer' backend='sf-databuffer' path=None delay=1.0 start=None end=None]
                        databuffer query arguments
  --retrieval [channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None delay=1.0 start=None end=None]
                        retrieval query arguments
  --dispatcher [channels path=None start=None end=None]
                        dispatcher query arguments
  --daqbuf [channels url='https://data-api.psi.ch/api/4' backend='sf-databuffer' path=None delay=1.0 cbor=True parallel=False start=None end=None]
                        daqbuf query arguments
  --array10 [channels url=None mode='SUB' path=None reshape=False start=None end=None]
                        array10 query arguments
```


Source specific help can be displayed as:

```bash
datahub --<SOURCE>
```
 
```
$ $ datahub --retrieval
Source Name: 
	retrieval
Arguments: 
	[channels url='https://data-api.psi.ch/api/1' backend='sf-databuffer' path=None delay=1.0 start=None end=None ...]
Default URL:
	https://data-api.psi.ch/api/1
Default Backend:
	sf-databuffer
Known Backends:
	sf-databuffer
	sf-imagebuffer
	hipa-archive
                                                                                                                                                                           
```

- If urls and backends are not specified in the command line arguments, sources utilize  default ones. 
Default URLs and backends can be redefined by environment variables:
    - `<SOURCE>_DEFAULT_URL`
    - `<SOURCE>_DEFAULT_BACKEND`

```bash
    export DAQBUF_DEFAULT_URL=https://data-api.psi.ch/api/4
    export DAQBUF_DEFAULT_BACKEND=sf-databuffer
```
      
- The following arguments (or their abbreviations) can be used as source arguments, 
overwriting the global arguments if present:
  - channels
  - start
  - end
  - id 
  - time
  - url
  - backend
  - path
  - interval
  - modulo
  - prefix 
  

In this example a hdf5 file will be generated  querying the next 10 pulses of S10BC01-DBPM010:Q1 from daqbuf, 
but also next 2 seconds of the EPICS channel S10BC01-DBPM010:X1:

```bash 
datahub -f tst.h5 -s 0 -e 10 -i -c S10BC01-DBPM010:Q1 --daqbuf delay 10.0 --epics s 0 e 2 time True c S10BC01-DBPM010:X1   
```
  
- Source specific arguments, unlike the global ones, don't start by '-' or '--'. Boolean argument values (such as for __id__ or __time__) must be explicitly typed.
      


Data can be potted  with the options --plot or --pshell.

This example will print and plot the values of an EPICS channel for 10 seconds:

```bash
datahub -p -s -0 -e 10 -c S10BC01-DBPM010:Q1 --epics --plot
```


A pshell plotting server can be started (in default per 7777) and used in datahub with:
```bash
pshell_op -test -plot -title=DataHub    
datahub ... -ps [PLOT OPTIONS] 
``` 

# Query range

The query ranges, specified by arguments __start__ and __end__, can be specified by time or ID, in absolute or relative values.
By default time range is used, unless the __id__ argument is set.
For time ranges values can be :
- Numeric, interpreted as a relative time to now (0). Ex: -10 means 10  seconds ago.
- Big numeric (> 10 days as ms), interpreted as a timestamp (millis sin EPOCH).
- String, an absolute timestamp ISO 8601, UTC or local time ('T' can be ommited).

For ID ranges, the  values can be:
- Absolute.
- Relative to now (if value < 100000000).
    

# Channel search

The __--search__ argument is used for searching channel names and info instead of querying data. 

- datahub --search --<SOURCE NAME> <PATTERN>

Example:

```bash
$ datahub --daqbuf --search SARFE10-PSSS059:FIT
           backend                     name            seriesId type  shape
     sf-databuffer  SARFE10-PSSS059:FIT-COM          1380690830          []
     sf-databuffer SARFE10-PSSS059:FIT-FWHM          1380690826          []
     sf-databuffer  SARFE10-PSSS059:FIT-RES          1380690831          []
     sf-databuffer  SARFE10-PSSS059:FIT-RMS          1380690827          []
     sf-databuffer  SARFE10-PSSS059:FIT_ERR          1380701106      [4, 4]
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-COM 7677120138367706877  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-COM 7677120138367706877  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-COM 7677120138367706877  f64     []
swissfel-daqbuf-ca SARFE10-PSSS059:FIT-FWHM 1535723503598383715  f64     []
swissfel-daqbuf-ca SARFE10-PSSS059:FIT-FWHM 1535723503598383715  f64     []
swissfel-daqbuf-ca SARFE10-PSSS059:FIT-FWHM 1535723503598383715  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RES 8682027960712655293  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RES 8682027960712655293  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RES 8682027960712655293  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RMS 8408394372370908679  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RMS 8408394372370908679  f64     []
swissfel-daqbuf-ca  SARFE10-PSSS059:FIT-RMS 8408394372370908679  f64     []
```

# Usage as library

- When used as a library datahub can be used to retrieve data in different patterns.  
- Sources are freely created and dynamically linked to consumers. 
- The tests provide examples.
- In memory operations can be performed: 
    - Using the __Table__ consumer, which allows retrieving data as a dictionary or a Pandas dataframe.
    - Extending the __Consumer__ class, and then receiving the data events asynchronously.  


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


## Paralelizing queries

Queries can be performed asynchronously, and therefore can be paralellized.
This example retrieves and saves data from a BSREAD source and from EPICS, for 3 seconds:


```python
from datahub import *


with Epics() as epics:
    with Bsread(url= "tcp://localhost:9999", mode="PULL") as bsread
        hdf5 = HDF5Writer("~/data.h5")
        stdout = Stdout()
        epics.add_listener(hdf5)
        epics.add_listener(stdout)
        bsread.add_listener(hdf5)
        bsread.add_listener(stdout)
        epics.req(["TESTIOC:TESTSINUS:SinCalc"], None, 3.0, background=True)
        bsread.req(["UInt8Scalar", "Float32Scalar"], None, 3.0, background=True)
        epics.join()
        bsread.join()
```

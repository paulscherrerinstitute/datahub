import sys
import numpy
from datahub.main import main

"""
json_str = '{' \
           '"file": "/Users/gobbo_a/dev/back/json.h5", ' \
           '"print": true, ' \
           '"epics": {"url": null, "query":{"start":null, "end":3.0, "channels": ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTWF2:MyWF"]}},' \
           '"bsread": {"url": "tcp://localhost:9999", "mode":"PULL", "query":{"start":null, "end":3.0, "channels":  ["UInt8Scalar", "Float32Scalar"]}}' \
           '}'
args = ["--json", json_str]
sys.argv=sys.argv + args
"""
"""
args = ["--search", "SARFE10-PSSS059:SPECTRUM_X", "--databuffer"]
sys.argv = sys.argv + args
"""
"""
args = ["-h"]
sys.argv = sys.argv + args
args = ["--daqbuf"]
sys.argv = sys.argv + args
args = ["--search", "S10CB01-RILK-RFDET:BLANKTIME"]
sys.argv = sys.argv + args
"""
#args = ["--daqbuf"]
# args = ["--daqbuf", "c", "S10BC01-DBPM010:Q1", "--daqbuf", "c", "S10BC01-DBPM010:X1", "b", "sf-databuffer", "-s", "-100", "-e", "-99.9", "-p"]
# args = ["--daqbuf", "c", "S10BC01-DBPM010:Q1", "/", "c", "S10BC01-DBPM010:X1", "b", "sf-databuffer", "-s","-100", "-e", "-99.9", "-p"]
# args = ["-f", "~/test.h5", "-b", "sls-archiver", "-s", "2025-03-21 17:00:00.000", "-e", "2025-03-24 02:00:00.000", "-n", "2000", "-c", "AGEBD-DBPM3CURR:CURRENT-AVG,AGEBD-LIFETIME:LIFETIME,AGEBD-LIFETIME:LOSSRATIO,ARIVA-VMAVE:PRESS-MAX,AGEBD-DBPM3CURR:ACCUMULATED-BEAM-DOSE"]
#args = ["--hdf5", "/Users/gobbo_a/test.h5", "--backend", "sls-archiver", "--start", "2025-03-21 17:00:00.000", "--end",
#        "2025-03-22 02:00:00.000", "--bins", "2000", "--channels", "AGEBD-LIFETIME:LOSSRATIO", "--daqbuf", "-p"]

#args = ["--camera", "name", "simulation", "u", "http://localhost:8888", "-s", "0", "-e", "1.0", "-p", "--hdf5", "/Users/gobbo_a/test.h5"]
args = [ "-u", "http://localhost:8888", "--camera", "name", "simulation3", "--camera", "name", "simulation4", "-c", "image", "-s", "0", "-e", "3", "-px", "-p",  "--align", "partial", "-f", "./tst.h5", "-tt", "str"]


sys.argv = sys.argv + args
main()

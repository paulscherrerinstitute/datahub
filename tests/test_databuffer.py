import unittest
from datahub import *
import time

backend = "sf-databuffer"
filename = "/Users/gobbo_a/dev/back/databuffer.h5"


channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:Y2"]
start = "2024-01-05T08:50:00.000Z"
end = "2024-01-05T08:50:05.000Z"

channels = ["S10BC01-DBPM010:Q1", ]
channels = ["SARFE10-PSSS059:SPECTRUM_X"]
start = "2024-02-14 08:50:00.000"
end = "2024-02-14 08:50:05.000"

#channels = ["SARES20-CAMS142-M5.processing_parameters"]
#start = "2024-02-14 16:50:00.000"
#end = "2024-02-14 16:50:05.000"


#start = 20319949320
#end =   20319949818

#start = 200
#end =   500

#start = -15.0
#end =   -12.0

query = {
    "channels": channels,
    "start": start,
    "end": end
}

class DataBufferTest(unittest.TestCase):
    def setUp(self):
        self.source = DataBuffer(backend=backend)

    def tearDown(self):
        self.source.close()

    def test_listeners(self):
        hdf5 = HDF5Writer(filename)
        stdout = Stdout()
        table = Table()
        self.source.add_listener(hdf5)
        self.source.add_listener(stdout)
        self.source.add_listener(table)
        self.source.request(query)
        dataframe = table.as_dataframe()
        self.source.close_listeners()


if __name__ == '__main__':
    unittest.main()

import time
import unittest
from datahub import *

url = "tcp://localhost:9999"
mode = "PULL"
filename = "/Users/gobbo_a/dev/back/bsread.h5"
channels = None
channels = ["UInt8Scalar", "Float32Scalar"]
start = 0.0
end = 2.1
query = {
    "channels": channels,
    "start": start,
    "end": end
}

class BsreadTest(unittest.TestCase):
    def setUp(self):
        self.source = Bsread(url=url, mode=mode, time_type="str")

    def tearDown(self):
        self.source.close()


    def test_listeners(self):
        hdf5 = HDF5Writer(filename, default_compression=Compression.GZIP)
        stdout = Stdout()
        table = Table()
        #self.source.set_id("bsread")
        self.source.add_listener(hdf5)
        self.source.add_listener(stdout)
        self.source.add_listener(table)
        self.source.request(query)
        self.source.req(channels, start, end, receive_timeout=5000)
        dataframe = table.as_dataframe()
        print(dataframe.columns)
        if channels:
            self.assertEqual(list(dataframe.keys()), channels)
        self.source.close_listeners()

if __name__ == '__main__':
    unittest.main()

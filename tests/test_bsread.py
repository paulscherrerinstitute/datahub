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
    "end": end,
    "filter": "UInt8Scalar<100"
}

class BsreadTest(unittest.TestCase):
    def setUp(self):
        self.source = Bsread(url=url, mode=mode, time_type="str")

    def tearDown(self):
        self.source.close()


    def test_listeners(self):
        #hdf5 = HDF5Writer(filename, default_compression=Compression.GZIP)
        stdout = Stdout()
        table = Table()
        #self.source.set_id("bsread")
        #self.source.add_listener(hdf5)
        self.source.add_listener(stdout)
        self.source.add_listener(table)
        self.source.request(query)
        self.source.req(channels, start, end, receive_timeout=5000, filter= "UInt8Scalar>100")
        dataframe = table.as_dataframe()
        print(dataframe.columns)
        if channels:
            self.assertEqual(list(dataframe.keys()), channels)
        self.source.close_listeners()

    def test_bsread_stream(self):
        with BsreadStream(url=url, mode=mode,time_type="str", channels=channels, filter= "UInt8Scalar<10") as source:
            for i in range(10):
                print(i, source.receive(1.0))

    def test_bsread_no_channels(self):
        stdout = Stdout()
        self.source.add_listener(stdout)
        self.source.req(None, 0.0, 1.0)

if __name__ == '__main__':
    unittest.main()

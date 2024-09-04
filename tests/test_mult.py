import time
import unittest
from datahub import *

filename = "/Users/gobbo_a/dev/back/mult.h5"
channels_epics = ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTWF2:MyWF"]
url_bsread = "tcp://localhost:9999"
mode_bsread= "PULL"
channels_bsread = ["UInt8Scalar", "Float32Scalar"]
start = None
end = 3.0


class EpicsTest(unittest.TestCase):
    def setUp(self):
        self.epics = Epics()
        self.bsread = Bsread(url=url_bsread, mode=mode_bsread)


    def tearDown(self):
        cleanup()


    def test_listeners(self):
        hdf5 = HDF5Writer(filename)
        stdout = Stdout()
        table = Table()
        self.epics.add_listener(hdf5)
        self.epics.add_listener(stdout)
        self.epics.add_listener(table)
        self.bsread.add_listener(hdf5)
        self.bsread.add_listener(stdout)
        self.bsread.add_listener(table)

        self.epics.req(channels_epics, start, end, background=True)
        self.bsread.req(channels_bsread, start, end, background=True)
        #time.sleep(1.0)
        #self.bsread.abort()
        self.epics.join()
        self.bsread.join()
        dataframe = table.as_dataframe()
        print (dataframe.columns)


if __name__ == '__main__':
    unittest.main()

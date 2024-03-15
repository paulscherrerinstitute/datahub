import unittest
from datahub import *


backend = "sf-imagebuffer"
#url = "https://data-api.psi.ch/api/1"
url = "http://sf-daq-5.psi.ch:8380/api/1"
#url = "http://127.0.0.1:7777/api/1"

#url = "https://data-api.psi.ch/api/1"
#url = "http://sf-daq-5.psi.ch:8380/api/1"
#url = "http://sf-daq-5.psi.ch/api/1"

filename = "ib.h5"
channels = ["SATES21-CAMS154-M2:FPICTURE"]
channels = ["SARFE10-PSSS059:FPICTURE"]
start = "2024-02-20 12:04:31.000"
end = "2024-02-20 12:04:32.000"

query = {
    "channels": channels,
    "start": start,
    "end": end
}


class RetrivalTest(unittest.TestCase):
    def setUp(self):
        self.source = Retrieval(url=url, backend=backend, auto_decompress=False)

    def tearDown(self):
        self.source.close()


    def test_listeners(self):
        hdf5 = HDF5Writer(filename)
        #stdout = Stdout()
        #table = Table()
        self.source.add_listener(hdf5)
        #self.source.add_listener(stdout)
        #self.source.add_listener(table)
        self.source.request(query)
        #dataframe = table.as_dataframe()
        #self.assertEqual(list(dataframe.keys()), channels)
        self.source.close_listeners()


if __name__ == '__main__':
    unittest.main()
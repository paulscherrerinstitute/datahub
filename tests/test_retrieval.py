import unittest
from datahub import *

backend = "sf-databuffer"


filename = "/Users/gobbo_a/dev/back/retrieval.h5"
#channels = ["SARFE10-PSSS059:FIT-COM", "SARFE10-PSSS059:FIT-FWHM"]
channels = ["S10BC01-DBPM010:Q1"]
start = "2024-02-14 08:50:00.000"
end = "2024-02-14 08:50:05.000"

#String channels not working
#channels = ["SARES20-CAMS142-M5.processing_parameters"]
#start = "2024-02-14 16:50:00.000"
#end = "2024-02-14 16:50:05.000"

#start = '2024-02-12T07:50:00.000000Z'
#end =  '2024-02-12T07:50:01.000000Z'

"""
query = {
    "channels": channels,
    "range": {
        "type": "date",
        "startDate": start,
        "endDate": end
    }
}
"""

query = {
    "channels": channels,
    "start": start,
    "end": end
}





class RetrivalTest(unittest.TestCase):
    def setUp(self):
        self.source = Retrieval(backend=backend)

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
        self.assertEqual(list(dataframe.keys()), channels)
        self.source.close_listeners()


if __name__ == '__main__':
    unittest.main()

import time
import unittest
from datahub import *

backend = "sf-databuffer"
filename = "/Users/gobbo_a/dev/back/daqbuf.h5"
filename = "/Users/gobbo_a/tst.h5"

channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"]
start = "2024-02-15T12:41:00Z"
end = "2024-02-15T12:42:00Z"

query = {
    "channels": channels,
    "start": start,
    "end": end
}

class DataBufferTest(unittest.TestCase):

    def test_listeners(self):
        parallel = True
        for index, parallel in [(Table.PULSE_ID, False), (Table.TIMESTAMP, True)]:
            with Daqbuf(backend=backend, cbor=True, parallel=parallel) as source:
                table = Table()
                source.add_listener(table)
                source.request(query)
                dataframe_cbor = table.as_dataframe(index)
                dataframe_cbor.reindex(sorted(dataframe_cbor.columns), axis=1)
                print (dataframe_cbor)

            with Daqbuf(backend=backend, cbor=False, parallel=parallel) as source:
                table = Table()
                source.add_listener(table)
                source.request(query)
                dataframe_json = table.as_dataframe(index)
                dataframe_json.reindex(sorted(dataframe_json.columns), axis=1)
                print(dataframe_json)
            self.assertEqual(dataframe_cbor.equals(dataframe_json), True)

    def test_save(self):
        s = time.time()
        with Daqbuf(backend=backend, cbor=True, parallel=True) as source:
            hdf5 = HDF5Writer(filename)
            source.add_listener(hdf5)
            channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"]
            start = "2024-05-02 09:00:00"
            end = "2024-05-02 10:00:00"
            source.req(channels, start, end)
        print (time.time()-s)

if __name__ == '__main__':
    unittest.main()

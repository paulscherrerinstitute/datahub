import time
import unittest
from datahub import *

backend = "sf-databuffer"
filename = "/Users/gobbo_a/dev/back/daqbuf.h5"
filename = "/Users/gobbo_a/datahub.h5"

channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"]
start = "2024-02-15T12:41:00Z"
end = "2024-02-15T12:42:00Z"

channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"]
start = "2024-06-14 09:00:00"
end = "2024-06-14 10:00:00"

query = {
    "channels": channels,
    "start": start,
    "end": end
}

class DataBufferTest(unittest.TestCase):

    def test_dataframe(self):
        with Daqbuf(backend=backend, cbor=True, parallel=True) as source:
            table = Table()
            source.add_listener(table)
            source.request(query)
            dataframe_cbor = table.as_dataframe(Table.PULSE_ID)
            dataframe_cbor.reindex(sorted(dataframe_cbor.columns), axis=1)
            print(dataframe_cbor)

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
            source.req(channels, start, end)
        print (time.time()-s)


    def test_listener(self):
        last = None
        class Listener(Consumer):
            def on_start(self, source):
                pass

            def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
                print(f"Started: {name}")

            def on_channel_record(self, source, name, timestamp, pulse_id, value):
                #print(f"{timestamp} {name}={str(value)} ")
                nonlocal last
                last = timestamp, pulse_id, value

            def on_channel_completed(self, source, name):
                timestamp, pulse_id, value = last
                timestr = convert_timestamp(timestamp, "str")
                print(f"Completed: {name}: {last} - {timestr}")

            def on_stop(self, source, exception):
                pass


        s = time.time()
        with Daqbuf(backend=backend, cbor=True, parallel=True) as source:
            source.add_listener(Listener())
            source.request(query)
        print (time.time()-s)


    def test_waveform(self):

        with Daqbuf(backend=backend, cbor=True, parallel=True) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.req(["SARFE10-PSSS059:SPECTRUM_X"], "2024-05-07 16:00:00", "2024-05-07 16:00:01", False)


    def test_backends(self):
        with Daqbuf() as source:
            print (source.get_backends())
            print(source.get_backends())

    def test_sf_archiver(self):

        with Daqbuf(backend="sf-archiver", cbor=True, parallel=True) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.req(["S10CB05-RBOC-DCP10:REF-POWER-AVG"], -1000, 0, False)


    def test_binned(self):
        query["bins"]=100
        with Daqbuf(backend=backend, cbor=True, parallel=False) as source:
            table = Table()
            source.add_listener(table)
            source.request(query)
            df = table.as_dataframe(Table.TIMESTAMP)
            df.reindex(sorted(df.columns), axis=1)
            print(df)

    def test_binned2(self):
        query["bins"]=100
        with Daqbuf(backend=backend, cbor=True, parallel=False) as source:
            stout = Stdout()
            source.add_listener(stout)
            source.request(query)

    def test_binned3(self):
        query["bins"]=100
        with Daqbuf(backend=backend, cbor=True, parallel=False) as source:
            plot = Plot()
            source.add_listener(plot)
            source.request(query)

    def test_binned4(self):
        query["bins"]=100
        with Daqbuf(backend=backend, cbor=True, parallel=False, time_type="millis") as source:
            stdout = Stdout()
            hdf5 = HDF5Writer(filename)
            source.add_listener(hdf5)
            source.add_listener(stdout)
            source.request(query)

if __name__ == '__main__':
    unittest.main()

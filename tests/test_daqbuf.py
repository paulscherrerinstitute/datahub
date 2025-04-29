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
start = "2024-09-15 09:00:00"
end = "2024-09-15 10:00:00"

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
        with Daqbuf(backend=backend, cbor=False, parallel=True,  time_type="str") as source:
            #table = Table()
            stout = Stdout()
            source.add_listener(stout)
            #source.request(query)
            source.req(["S10BC01-DBPM010:Q1","S10BC01-DBPM010:X1",],None, None, range="Last 1min",  bins=100)
            #source.req(["ARS05-RCIR-0060:Water-Flow",],"2024-09-15 09:00", "2024-09-15 10:00", bins=100, backend="sls-archiver")
            #source.req(["SARFE10-PSSS059:FIT-COM",],"2024-09-26 08:57:57.510", "2024-09-26 09:57:57.510", bins=100)
            #source.req(["SARFE10-PSSS059:FIT-COM", ], "2024-09-26 08:57:57.510", "2024-09-26 09:00:57.510")
            #df = table.as_dataframe(Table.TIMESTAMP)
            #df.reindex(sorted(df.columns), axis=1)
            #print(df)

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

    def test_enums(self):
        with Daqbuf(backend="sf-archiver", cbor=True, parallel=False) as source:
            stdout = Stdout()
            source.search("SOFTMPS:L1-MA-OK")
            source.add_listener(stdout)
            #plot = Plot()
            plot = PShell()
            source.add_listener(plot)
            hdf5 = HDF5Writer(filename)
            source.add_listener(hdf5)

            table = Table()
            source.add_listener(table)

            source.req(["SOFTMPS:L1-MA-OK", "S10CB03-RHLA-JOBMON:VME-TEMP-AVG"], -100000.0, 0.0)
            print (table.as_dataframe(Table.TIMESTAMP))

    def test_enums_2(self):
        query = {
            "channels": ["SOFTMPS:L1-MA-OK", "SOFTMPS:L1-AR-OK", "SOFTMPS:L1-AT-OK"],
            "start": "2024-09-05 08:00:00.000",
            "end": "2024-09-05 11:30:00.000"
        }
        with Daqbuf(backend="sf-archiver") as source:
            table = Table()
            source.add_listener(table)
            source.request(query)
            print(table.as_dataframe())


    def test_erik(self):
        query = {'start': '2024-01-16 10:14:25', 'end': '2024-01-16 10:40', 'channels': ['S10BC01-DBPM050:Q2', 'S10BC01-DBPM050:Q2-VALID']}
        with Daqbuf(backend="sf-databuffer") as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.request(query)
            #print(table.as_dataframe())

    def test_erik2(self):
        query = {'start': '2024-01-16 10:14:25', 'end': '2024-01-16 10:40',
                 'channels': ['S10BC01-DBPM050:Q2', 'S10BC01-DBPM050:Q2-VALID']}
        with DataBuffer(backend="sf-databuffer") as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.request(query)

    def test_erik3(self):
        queries = [
            {'start': '2025-02-24 10:33:18', 'end': '2025-02-24 10:33:28', 'channels': ['SARFE10-PSSS059:FIT-RES', 'SARFE10-PSSS059:FIT-RMS', '9014575066011828102']},
            #{'start': '2025-02-24 10:33:18', 'end': '2025-02-24 10:33:28', 'channels': ['SARFE10-PSSS059:FIT-RMS']} ,
            #{'start': '2025-02-24 10:33:18', 'end': '2025-02-24 10:33:28', 'channels': ['#9014575066011828102']}
        ]
        with Daqbuf(backend="sf-archiver") as source:
            stdout = Stdout()
            source.add_listener(stdout)
            for query in queries:
                source.request(query)

    def test_search(self):
        with Daqbuf(backend="sf-archiver", cbor=True, parallel=False) as source:
            print (source.search("", case_sensitive=False))



if __name__ == '__main__':
    unittest.main()

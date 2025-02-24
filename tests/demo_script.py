from datahub import *
import subprocess
FILE_NAME = "/Users/gobbo_a/datahub.h5"
# Open HDF5 file
def open_hdf5():
    subprocess.Popen(["pshell", "-dtpn", f"-f={FILE_NAME}"])


####################################################################################################
# A simple query on Daqbuf with multiple listeners
####################################################################################################
with Daqbuf(backend="sf-databuffer", cbor=True, parallel=True) as daq:
    query = { "channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
              "start": "2025-01-30 09:00:00",
              "end": "2025-01-30 09:01:00"}
    daq.add_listener(Stdout())
    daq.add_listener(PShell())
    daq.add_listener(HDF5Writer("/Users/gobbo_a/datahub.h5"))
    daq.request(query)
    daq.close_listeners()


####################################################################################################
# Multiple sources sending data to HDF5 and plot
####################################################################################################
with HDF5Writer(FILE_NAME) as h5:
    with PShell() as ps:
        with Daqbuf(backend="sf-archiver", cbor=True, parallel=True) as daq1:
            daq1.add_listener(ps)
            daq1.add_listener(h5)
            with Daqbuf(backend="sls-archiver", cbor=True, parallel=True) as daq2:
                daq2.add_listener(ps)
                daq2.add_listener(h5)
                with Epics(url="localhost:54321") as ca:
                    ca.add_listener(ps)
                    ca.add_listener(h5)
                    with Bsread(url="tcp://localhost:9999") as bs:
                        bs.add_listener(ps)
                        bs.add_listener(h5)
                        daq1.req(["S10BC01-DBPM010:Q1"], -60.0, 0.0, background=True)
                        daq2.req(["ARS09-VMCC-1550:PRESSURE"], -60.0, 0.0, background=True)
                        ca.req(["TESTIOC:TESTSINUS:SinCalc"], 0.0, 2.0, background=True)
                        bs.req(["UInt8Scalar","Float64Scalar"], 0.0, 2.0, background=True)
                        daq1.join()
                        daq2.join()
                        ca.join()
                        bs.join()
# Open HDF5 file
open_hdf5()


####################################################################################################
# Creating a Custom Consumer
####################################################################################################
class Listener (Consumer):
    def on_start(self, source):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        print(f"---------------------------------------------------------------------------")
        print(f"Started: {name} @ {source.get_backend()}")

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        print(f"Received: {timestamp} {name}={str(value)} ")

    def on_channel_completed(self, source, name):
        print(f"Completed: {name} @ {source.get_backend()}")
        print(f"---------------------------------------------------------------------------")

    def on_stop(self, source, exception):
        pass

with Daqbuf(backend="sls-archiver", cbor=True, parallel=True) as daq:
    listener = Listener()
    daq.add_listener(listener)
    daq.req(["ARS09-VMCC-1550:PRESSURE"], -60.0, -50.0)


####################################################################################################
# Querying data as Pandas dataframes or dictionaries
####################################################################################################
query = {
    "channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
    "start": "2025-01-30 12:50:00.000",
    "end": "2025-01-30 12:50:00.100"
}
with Daqbuf(backend="sf-databuffer") as daq:
    table = Table()
    daq.add_listener(table)
    daq.request(query)
    print(f"---------------------------------------------------------------------------")
    print (table.data)
    print(f"---------------------------------------------------------------------------")
    dataframe = table.as_dataframe(Table.PULSE_ID)
    print(dataframe)
    print(f"---------------------------------------------------------------------------")


####################################################################################################
# A BSREAD query with filter
####################################################################################################
url = "tcp://localhost:9999"
mode = "PULL"
channels = ["UInt8Scalar", "Float64Scalar"]
start = 0.0
end = 2.1
query = {
    "channels": channels,
    "start": start,
    "end": end,
    "filter": "UInt8Scalar<100"
}
with PShell() as ps:
    with Bsread(url=url, mode=mode, time_type="str") as bs:
        bs.add_listener(ps)
        bs.request(query, background=False)


####################################################################################################
# Receiving bsread as a stream
####################################################################################################
with BsreadStream(url="tcp://localhost:9999", mode="PULL", time_type="str", channels= ["UInt8Scalar", "Float64Scalar"], filter="UInt8Scalar<10") as source:
    for i in range(10):
        print(i, source.receive(1.0))


####################################################################################################
# Create a pipeline with aditional config
####################################################################################################
with Pipeline(url="http://localhost:8889", name="[simulation3_sp]", config = {"binning_x":2,"binning_y":2}) as source:
    stdout = Stdout()
    source.add_listener(stdout)
    source.req(start=0.0, end=1.0, channels=["width", "height"])
    stdout.close()


####################################################################################################
# Image buffer
####################################################################################################
#query = {"channels":  ["SARFE10-PSSS059:FPICTURE"], "start": "2025-01-30 12:04:31.000", "end": "2025-01-30 12:04:32.000"}
#with HDF5Writer(FILE_NAME) as h5:
#    with Retrieval(url="http://sf-daq-5.psi.ch:8380/api/1", backend="sf-imagebuffer", auto_decompress=False) as ib:
#        ib.add_listener(h5)
#        ib.request(query)
#open_hdf5()


####################################################################################################
# Merging streams
####################################################################################################
start = "2025-01-30 09:00:00"
end = "2025-01-30 09:01:00"
backend = "sf-databuffer"""
with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="str") as daq1:
    with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="str") as daq2:
        stdout =Stdout()
        merger=Merger(filter = "S10BC01-DBPM010:X1<0")
        daq1.add_listener(merger)
        daq2.add_listener(merger)
        merger.to_source().add_listener(stdout)
        daq1.req(["S10BC01-DBPM010:Q1"], start, end, background=True)
        daq2.req(["S10BC01-DBPM010:X1"], start, end, background=True)
        daq1.join()
        daq2.join()


####################################################################################################
#Search for names -> Pandsas dataframe
####################################################################################################
with Daqbuf(backend="sf-databuffer") as daq:
    print(daq.search("AVG"))

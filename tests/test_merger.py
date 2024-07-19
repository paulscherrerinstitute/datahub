from datahub import *

start = "2024-06-14 09:00:00"
end = "2024-06-14 09:01:00"
backend = "sf-databuffer"





with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="str") as stream1:
    with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="str") as stream2:
        stdout =Stdout()
        merger=Merger(filter = "S10BC01-DBPM010:X1>0")

        stream1.add_listener(merger)
        stream2.add_listener(merger)

        merger.to_source().add_listener(stdout)

        stream1.req(["S10BC01-DBPM010:Q1"], start, end, background=True)
        stream2.req(["S10BC01-DBPM010:X1"], start, end, background=True)
        stream1.join()
        stream2.join()

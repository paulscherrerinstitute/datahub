import unittest
import os
os.environ["REDIS_DEFAULT_URL"] = "std-daq-build:6379"
from datahub import *
import time
channels = ['channel1', 'channel2', 'channel3',  'array1',  'array2']

class DataBufferTest(unittest.TestCase):

    def test_redis_print(self):
            #with Plot() as plot:
            with Stdout() as stdout:
            #with HDF5Writer("/Users/gobbo_a/dev/back/redis.h5") as h5:
                    with Redis(time_type="str") as source:
                        #src_ch = source.search("chann");
                        #src_db = source.search();
                        source.add_listener(stdout)
                        #source.add_listener(plot)
                        #source.add_listener(h5)
                        source.req(channels, 0.0, 2.0, partial_msg=False)

    def test_redis_dataframe(self):
            with Table() as table:
                with Redis(time_type="str") as source:
                    source.add_listener(table)
                    source.req(channels, 0.0, 1.0)
                    df = table.as_dataframe(index=Table.TIMESTAMP)
                    print(df)
                    df = table.as_dataframe(index=Table.PULSE_ID)
                    print(df)


    def test_redis_strm(self):
        with RedisStream(channels, time_type="str", partial_msg=False) as source:
            for i in range(100):
                print(i, source.receive(1.0))
        #with RedisStream(channels, time_type="str", filter="(channel3>0.5 AND channel1<0.5) OR channel2<0.1") as source:
        #    for i in range(10):
        #        print(i, source.receive(1.0))

    def test_redis_stream_as_bsread(self):
        with RedisStream(channels) as source:
            source.forward_bsread(5678)

    def test_redis_stream(self):
        # with RedisStream(channels, time_type="str") as source:
        #    for i in range(1000):
        #        print(i, source.receive(1.0))
        # with RedisStream(channels, time_type="str", filter="(channel3>0.5 AND channel1<0.5) OR channel2<0.1") as source:
        #    for i in range(10):
        #        print(i, source.receive(1.0))
        buf = []
        start = time.time()
        end = start + 6.0

        with RedisStream(channels, time_type="str", queue_size=100, size_align_buffer=1000, partial_msg="after") as source:
            while time.time() < end:
                rec = source.receive(1.0)
                if rec:
                    buf.append(rec[0])
                    if len(rec[2]) != len(channels):
                        print(
                            f"Partial message on {time.time() - start} at index {len(buf)} id:{buf[-1]} - keys: {rec[2].keys()}")
                else:
                    print(f"Null message on {time.time() - start} after index {len(buf)} id:{buf[-1] if buf else None}")
            print(f"Number Records: {len(buf)}")

            min_index = buf[0]
            max_index = buf[-1]
            full_range = set(range(min_index, max_index + 1))
            missing_records = sorted(full_range - set(rec for rec in buf))
            missing_indices = [i - min_index for i in missing_records]
            print(f"Number missing: {len(missing_records)}")
            print(f"Missing records: {missing_records}")
            print(f"Missing indices: {missing_indices}")

    def test_redis_merger(self):
        with Redis(time_type="str") as stream1:
            with Redis(time_type="str") as stream2:
                stdout =Stdout()
                merger=Merger(filter="channel1>0.5")

                stream1.add_listener(merger)
                stream2.add_listener(merger)
                merger.to_source().add_listener(stdout)

                stream1.req(["channel1"], 0.0, 2.0, background=True, filter = "channel1>0.5")
                stream2.req(["channel2"], 0.0, 2.0, background=True)
                stream1.join()
                stream2.join()


if __name__ == '__main__':
    unittest.main()

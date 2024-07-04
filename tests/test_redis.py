#import redis
#with redis.Redis(host='std-daq-build',port=6379,db=0) as rc:
#    rc.set('test:hello','World')
#    print(rc.get('test:hello'))
#rc.set('test:cnt', 1)
#print(rc.get('test:cnt'))
#rc.lpush("test:l1", "v1", "v2")
#print(rc.lindex('test:l1', 0))
#print(rc.lrange('test:l1', 0, -1))
#print(rc.keys('test:*'))

import unittest
from datahub import *
import time
channels = ['channel1', 'channel2', 'channel3']

class DataBufferTest(unittest.TestCase):
    """
    def test_redis_print(self):
        with Plot() as plot:
            with Stdout() as stdout:
                with Redis(time_type="str") as source:
                    src_ch = source.search("chann");
                    src_db = source.search();
                    source.add_listener(stdout)
                    source.add_listener(plot)
                    source.req(channels, 0.0, 2.0)

    def test_redis_dataframe(self):
            with Table() as table:
                with Redis(time_type="str") as source:
                    source.add_listener(table)
                    source.req(channels, 0.0, 5.0)
                    df = table.as_dataframe(index=Table.TIMESTAMP)
                    print(df)
                    df = table.as_dataframe(index=Table.PULSE_ID)
                    print(df)

    """
    def test_redis_stream(self):
        with RedisStream(channels, time_type="str", filter="(channel3>0.5 AND channel1<0.5) OR channel2<0.1") as source:
            for i in range(10):
                print(i, source.receive(1.0))



if __name__ == '__main__':
    unittest.main()

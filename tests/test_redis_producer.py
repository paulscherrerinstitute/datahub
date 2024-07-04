from datahub import *
from datahub.utils.data import *
import redis
import time
import threading
import random

MAX_STREAM_LENGHT = 1000
def produce(channel_name):
    stream = channel_name
    try:
        with redis.Redis(host='std-daq-build', port=6379, db=0) as r:
            now = time.time()
            id = time_to_pulse_id(now)
            while(True):
                timestamp = create_timestamp(now)
                value = random.random()
                #if channel_name== 'channel3':
                #   value = ">>>"+str(value)
                r.xadd(stream, {'channel': channel_name, 'timestamp': timestamp, 'value': encode(value), 'id': id}, maxlen=MAX_STREAM_LENGHT)
                #print(id, channel_name)
                #r.xtrim(stream, maxlen=MAX_STREAM_LENGHT, approximate=False)
                while True:
                    time.sleep(0.001) #100Hz
                    now = time.time()
                    new_id = time_to_pulse_id(now)
                    if new_id != id:
                        id = new_id
                        break
    except Exception as e:
        print(e)

def produce_mult(channel_prefix, index_range):
    try:
        with redis.Redis(host='std-daq-build', port=6379, db=0) as r:
            now = time.time()
            id = time_to_pulse_id(now)
            while(True):
                timestamp = create_timestamp(now)

                pipeline = r.pipeline()
                for i in index_range:
                    stream = channel_prefix + str(i)
                    value = random.random()
                    pipeline.xadd(stream, {'channel': stream, 'timestamp': timestamp, 'value': encode(value), 'id': id}, maxlen=MAX_STREAM_LENGHT)
                pipeline.execute()

                while True:
                    time.sleep(0.001) #100Hz
                    now = time.time()
                    new_id = time_to_pulse_id(now)
                    if new_id != id:
                        id = new_id
                        break
    except Exception as e:
        print(e)



if __name__ == '__main__':
    channels = ['channel1', 'channel2', 'channel3']
    threads = []
    if False:
        for channel in channels:
            thread = threading.Thread(target=produce, args=(channel,))
            threads.append(thread)
            thread.start()
    else:
        thread = threading.Thread(target=produce_mult, args=("channel",range(1,4)))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

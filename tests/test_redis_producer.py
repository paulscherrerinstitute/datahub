from datahub import *
import redis
import time
import threading
import random

MAX_STREAM_LENGHT = 1000
def produce(channel_name):
    stream = channel_name
    try:
        with redis.Redis(host='std-daq-build', port=6379, db=0) as r:
            while(True):
                now = time.time()
                id = time_to_pulse_id(now)
                timestamp = create_timestamp(now)
                value = random.random()
                r.xadd(stream, {'channel': channel_name, 'timestamp': timestamp, 'value': value, 'id': id})
                r.xtrim(stream, maxlen=MAX_STREAM_LENGHT, approximate=False)
                time.sleep(0.01) #100Hz
    except Exception as e:
        print(e)




if __name__ == '__main__':
    channels = ['channel1', 'channel2', 'channel3']
    threads = []
    for channel in channels:
        thread = threading.Thread(target=produce, args=(channel,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

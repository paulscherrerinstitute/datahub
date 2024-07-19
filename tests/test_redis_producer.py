from datahub import *
from datahub.utils.data import *
import redis
import time
import threading
import random

DEFAULT_URL = os.environ.get("REDIS_DEFAULT_URL", 'sf-daqsync-18:6379')
HOST, PORT = get_host_port_from_stream_address(DEFAULT_URL)

def ingest(r, stream, data, max_stream_lenght=1000):
    if not isinstance(stream, (list, tuple)):
        stream, data = [stream], [data]
    if len(stream) == 1:
        r.xadd(stream[0], data[0], maxlen=max_stream_lenght)
    else:
        pipeline = r.pipeline()
        for i in range(len(stream)):
            pipeline.xadd(stream[i], data[i], maxlen=max_stream_lenght)
        pipeline.execute()

def ingest_bsdata(r, pulse_id, timestamp, data, max_stream_lenght=1000):
    channels = list(data.keys())
    data = [{'channel': channel, 'timestamp': timestamp, 'value': encode(data[channel]), 'id': pulse_id} for channel in channels]
    ingest(r, channels, data, max_stream_lenght)


def wait_new_id(id):
    while True:
        time.sleep(0.001)  # 100Hz
        now = time.time()
        new_id = time_to_pulse_id(now)
        if new_id != id:
            return new_id, create_timestamp(now)

def produce_single(channel):
    try:
        with redis.Redis(host=HOST, port=PORT, db=0) as r:
            now = time.time()
            id, timestamp = time_to_pulse_id(now), create_timestamp(now)
            while(True):
                value = random.random()
                #data = {'channel': channel, 'timestamp': timestamp, 'value': encode(value), 'id': id}
                #ingest(r, channel, data)
                data = {channel: value}
                ingest_bsdata(r, id, timestamp, data)
                id, timestamp = wait_new_id(id)

    except Exception as e:
        print(e)

def produce_batch(channels):
    try:
        with redis.Redis(host=HOST, port=PORT, db=0) as r:
            now = time.time()
            id, timestamp = time_to_pulse_id(now), create_timestamp(now)
            while(True):
                #data =[{'channel': channel, 'timestamp': timestamp, 'value': encode(random.random()), 'id': id} for channel in channels]
                #ingest(r, channels, data)
                data = {channel: random.random() for channel in channels}
                ingest_bsdata(r, id, timestamp, data)
                id, timestamp = wait_new_id(id)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    batch = True
    channels = range(1, 4)
    threads = []
    if batch:
        thread = threading.Thread(target=produce_batch, args=([f"channel{i}" for i in channels],))
        threads.append(thread)
        thread.start()
    else:
        for channel in channels:
            thread = threading.Thread(target=produce_single, args=(f"channel{channel}",))
            threads.append(thread)
            thread.start()
    for thread in threads:
        thread.join()

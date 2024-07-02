import redis
import time
from datahub.utils.data import *
import logging
import pickle
_logger = logging.getLogger(__name__)


def on_msg(msg):
    #print(msg)
    pass

def fetch_aligned_data(r, channels, group_name, consumer_name, send_partial_msg=True):
    ids = set()
    group_name = generate_random_string(16)
    for channel in channels:
        try:
            r.xgroup_create(channel, group_name, mkstream=False)
        except Exception as e:
            print(e)
    try:
        sent_id = -1
        streams = {}
        num_channels = len(channels)
        size_align_buffer = 1000
        for channel in channels:
            streams[channel] = ">"
        aligned_data = MaxLenDict(maxlen=size_align_buffer)
        while True:
            entries = r.xreadgroup(group_name, consumer_name, streams, count=10*num_channels, block=200)
            for stream, messages in entries:
                for message_id, message_data in messages:
                    channel = message_data[b'channel'].decode('utf-8')
                    timestamp = int(message_data[b'timestamp'].decode('utf-8'))
                    id = int(message_data[b'id'].decode('utf-8'))
                    ids.add(id)
                    data = message_data[b'value']#.decode('utf-8')
                    value = decode(data)
                    if id not in aligned_data:
                        aligned_data[id] = {}
                        aligned_data[id]["timestamp"] = timestamp
                    aligned_data[id][channel] = value
                    r.xack(stream, group_name, message_id)  # Acknowledge message

            keys_in_order = sorted(list(aligned_data.keys()))
            last_complete_id = -1
            for i in range(len(keys_in_order)-1, 0, -1):
                id = keys_in_order[i]
                val = aligned_data[id]
                complete = len(val) == num_channels + 1
                if complete:
                    last_complete_id = id
                    break
            for i in range(len(keys_in_order)):
                id = keys_in_order[i]
                val = aligned_data[id]
                complete = len(val) == num_channels + 1
                done = False
                if complete:
                    done = True
                elif last_complete_id > id:
                    done = True
                elif len(aligned_data) > (size_align_buffer/2):
                    done = True

                if done:
                    # print ("    - ", id)
                    val = aligned_data.pop(id)
                    if complete or send_partial_msg:
                        if sent_id >= id:
                            print (f"Invalid ID {id} - last sent ID {sent_id}")
                        else:
                           expected = sent_id + 1
                           if (sent_id != -1) and (expected != id):
                               print(f"Missed ID {expected} - received {id}")
                               print(expected in ids, id in ids)
                           msg = collections.OrderedDict()
                           msg["id"] = id
                           msg["timestamp"] = val.get("timestamp", None)
                           for channel in channels:
                               msg[channel] = val.get(channel, None)
                           on_msg(msg)
                           sent_id = id
                    else:
                        logging.debug(f"Discarding partial message: {id}")

            if len(aligned_data) > 10:
                print ("--->", len(aligned_data))
            time.sleep(0.01)
    finally:
        for channel in channels:
            try:
                r.xgroup_destroy(channel, group_name)
            except Exception as e:
                print(e)
if __name__ == '__main__':
    channels = ['channel1', 'channel2', 'channel3']
    with redis.Redis(host='std-daq-build', port=6379, db=0) as r:
        fetch_aligned_data(r, channels, 'mygroup', 'consumer1')

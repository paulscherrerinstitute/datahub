import redis
import time

def fetch_aligned_data(r, channels, group_name, consumer_name):
    # Create the consumer group if it doesn't exist
    #try:
    #    r.xgroup_create('mystream', group_name, mkstream=True)
    #except redis.exceptions.ResponseError:
    #    pass  # Ignore if the group already exists

    group_name = 'mygroup2'

    streams = []
    for channel in channels:
        stream_name=channel
        try:
            r.xgroup_create(channel, group_name, mkstream=True)
        except redis.exceptions.ResponseError as e:
            print(f"Consumer group {group_name} for stream {stream_name} already exists.")

    while True:
        aligned_data = {}
        for channel in channels:
            stream_name = channel
            #entries = r.xreadgroup(group_name, consumer_name, {'mystream': '>'}, count=100, block=5000)
            entries = r.xreadgroup(group_name, consumer_name, {stream_name: '>'}, count=100, block=5000)
            if entries:
                stream, messages = entries[0]
                for message_id, message_data in messages:
                    channel = message_data[b'channel'].decode('utf-8')
                    timestamp = int(message_data[b'timestamp'].decode('utf-8'))
                    id = int(message_data[b'id'].decode('utf-8'))
                    value = message_data[b'value'].decode('utf-8')

                    if id not in aligned_data:
                        aligned_data[id] = {}
                    #aligned_data[channel].append((message_id.decode('utf-8'), timestamp, value))
                    aligned_data[id][channel] = value

                    # Acknowledge message
                    r.xack('mystream', group_name, message_id)

        # Process aligned data
        print (aligned_data)
        #for channel, data in aligned_data.items():
        #    print(f"Channel: {channel}")
        #    for entry in data:
        #        print(f"ID: {entry[0]}, Timestamp: {entry[1]}, Value: {entry[2]}")

        time.sleep(1)

if __name__ == '__main__':
    channels = ['channel1', 'channel2', 'channel3']
    with redis.Redis(host='std-daq-build', port=6379, db=0) as r:
        fetch_aligned_data(r, channels, 'mygroup', 'consumer1')

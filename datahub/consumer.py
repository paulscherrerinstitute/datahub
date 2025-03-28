from datahub.utils.timing import convert_timestamp
from datahub import str_to_bool

class Consumer:
    instances = set()

    def __init__(self, timetype=None, append=False, **kwargs):
        Consumer.instances.add(self)
        self.time_type = timetype
        self.append = str_to_bool(append)

    def on_start(self, source):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        pass

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        pass

    def on_channel_completed(self, source, name):
        pass

    def on_stop(self, source, exception):
        pass

    def on_close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def convert_time(self, timestamp, time_type):
        return convert_timestamp(timestamp, time_type, self.time_type)

    def close(self):
        self.on_close()
        if self in Consumer.instances:
            Consumer.instances.remove(self)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @staticmethod
    def cleanup():
        for consumer in list(Consumer.instances):
            consumer.close()

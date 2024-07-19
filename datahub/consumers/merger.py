from datahub import Consumer, Source
from datahub.utils.align import *

class Merger (Consumer):
    def __init__(self,  callback=None, filter=None, partial_msg=True, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.channels = {}
        self.align = Align(self.on_received_message, None, range=None, filter=filter, partial_msg=partial_msg)
        self.callback = callback

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        if self.align:
            self.align.add(pulse_id, timestamp, name, value)
            self.align.process()

    def on_start(self, source):
        self.channels[source] = source.query.get("channels",[])
        if len(self.channels) >1:
            channels = []
            for source, ch in self.channels.items():
                channels = channels + ch
            self.align.set_channels(channels)

    def on_stop(self, source, exception):
        del self.channels[source]
        if len(self.channels) == 0:
            self.align.set_channels(None)
            self.align.reset()

    def on_received_message(self, id, timestamp, msg):
        if self.callback:
            self.callback(id, timestamp, msg)

    def to_source(self):
        class MergerSource (Source):
            def __init__(self, merger, **kwargs):
                Source.__init__(self, **kwargs)
                self.merger = merger;
                self.merger.callback = self.on_received_message

            def on_received_message(self, id, timestamp, msg):
                for channel, value in msg.items():
                    self.receive_channel(channel, value, timestamp, id, check_changes=True)
        return MergerSource(self)
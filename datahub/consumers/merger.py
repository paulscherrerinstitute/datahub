from datahub import Consumer, Source, str_to_bool
from datahub.utils.align import *

class Merger (Consumer):
    def __init__(self,  callback=None, filter=None, partial_msg=True, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.channels = {}
        partial_msg = str_to_bool(partial_msg)
        self.align = Align(self.on_received_message, None, range=None, filter=filter, partial_msg=partial_msg)
        self.callback_on_message = callback
        self.callback_on_start = kwargs.get("on_start")
        self.callback_on_stop = kwargs.get("on_stop")
        self.sources = []

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
        else:
            if self.callback_on_start:
                self.callback_on_start()


    def on_stop(self, source, exception):
        del self.channels[source]
        if len(self.channels) == 0:
            self.align.set_channels(None)
            self.align.reset()
            if self.callback_on_stop:
                self.callback_on_stop()

    def on_received_message(self, id, timestamp, msg):
        if self.callback_on_message:
            self.callback_on_message(id, timestamp, msg)

    def get_sources(self):
        return self.sources

    def add_source(self, source):
        self.sources.append(source)
        source.time_type = "nano"  #Make all sources use nanos for timestamp
        source.add_listener(self)

    def to_source(self):
        class Merger (Source):
            def __init__(self, merger, **kwargs):
                Source.__init__(self, **kwargs)
                self.merger = merger;
                self.merger.callback_on_message = self.on_received_message
                self.merger.callback_on_start = self.on_started
                self.merger.callback_on_stop = self.on_stopped

            def on_started(self):
                self.create_query_id()
                self.on_start()

            def on_stopped(self):
                self.on_stop()

            def on_received_message(self, id, timestamp, msg):
                for channel, value in msg.items():
                    self.receive_channel(channel, value, timestamp, id, check_changes=True)

        return Merger(self)
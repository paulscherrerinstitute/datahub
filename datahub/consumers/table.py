import logging
from datahub import Consumer

_logger = logging.getLogger(__name__)


class Table(Consumer):
    TIMESTAMP = "timestamp"
    PULSE_ID = "pulse_id"
    def __init__(self, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.data = {}

    def on_close(self):
        self.data = {}

    def on_start(self, source):
        pass

    def on_stop(self, source, exception):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        self.data[name] = []

    def on_channel_record(self, source, name, timestamp, pulse_id, value):
        self.data[name].append({Table.TIMESTAMP: timestamp, Table.PULSE_ID: pulse_id, name: value})

    def on_channel_completed(self, source, name):
        pass

    def as_dataframe(self, index=TIMESTAMP):
        import pandas as pd
        dataframe = None
        drop = Table.PULSE_ID if index!=Table.PULSE_ID else Table.TIMESTAMP
        for key in self.data:
            values = self.data[key]
            if values is not None and (len(values) > 0):
                df = pd.DataFrame(self.data[key])
                df = df.drop(columns=[drop])
                df = df.set_index(index)

                if dataframe is None:
                    dataframe = df
                else:
                    dataframe = pd.merge(dataframe, df, how='outer', on=index)
        if dataframe is not None:
            # fill NaN with last known value (assuming recording system worked without error)
            dataframe.fillna(method='pad', inplace=True)
        return dataframe

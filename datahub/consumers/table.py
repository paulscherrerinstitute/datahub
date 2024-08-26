import logging
from datahub import Consumer

_logger = logging.getLogger(__name__)


class Table(Consumer):
    TIMESTAMP = "timestamp"
    PULSE_ID = "pulse_id"
    def __init__(self, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.clear()

    def clear(self):
        self.data = {}

    def on_close(self):
        self.clear()

    def on_start(self, source):
        pass

    def on_stop(self, source, exception):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        self.data[name] = []
        if (metadata.get("bins", None)):
            for col in "max", "min", "count":
                self.data[f"{name} {col}"] = []

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        self.data[name].append({Table.TIMESTAMP: timestamp, Table.PULSE_ID: pulse_id, name: value})
        if kwargs.get("bins", None):
            for col in "max", "min", "count":
                arg_name = f"{name} {col}"
                self.data[arg_name].append({Table.TIMESTAMP: timestamp, Table.PULSE_ID: pulse_id, arg_name: kwargs[col]})

    def on_channel_completed(self, source, name):
        pass

    def as_dataframe(self, index=TIMESTAMP, replace_nan=False):
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
        if (dataframe is not None) and replace_nan:
            #Fill NA/NaN values by propagating the last valid observation to next valid.
            dataframe.ffill(inplace=True)
        if (dataframe is not None):
            dataframe.sort_index(inplace=True)
        return dataframe

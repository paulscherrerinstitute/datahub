import logging
import numpy
import os
from datahub import Consumer

_logger = logging.getLogger(__name__)

class TextWriter(Consumer):

    def __init__(self, folder: str, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.folder = folder
        self.files = {}

    def on_start(self, source):
        os.makedirs(self.folder, exist_ok=True)
        self.files[source]={}

    def on_stop(self, source, exception):
        try:
            for f in self.files[source]:
                f.close()
            del self.files[source]
        except:
            pass

    def get_path(self, source, name):
        return f"{self.folder}/{name}"

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        if len(shape)<2:
            filename = self.get_path(source, name)
            self.files[source][name] = open(filename, 'a')

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        file = self.files[source].get(name, None)
        if file:
            trailer = ""
            if type(value) == bytes:
                value = f"bytes({len(value)})"
            elif isinstance(value, numpy.ndarray) and (len(value.shape) == 1):
                #value = numpy.array_str(value, max_line_width=numpy.inf)
                value = ' '.join(map(str, value))
                trailer = " " #Marker for array
            else:
                value = str(value)
            file.write(f"{str(timestamp)}\t{str(pulse_id)}\t{value}{trailer}\n")

    def on_channel_completed(self, source, name):
        try:
            del self.files[source][name]
        except:
            pass

    def on_close(self):
        for src, files in self.files.items():
            try:
                for f in files:
                    f.close()
            except:
                pass
        self.files = {}

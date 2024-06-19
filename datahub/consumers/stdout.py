import logging
import numpy as np
from datahub import Consumer
from datahub.utils.timing import timestamp_to_string

_logger = logging.getLogger(__name__)

class TextColors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

class Stdout(Consumer):
    def __init__(self,  **kwargs):
        Consumer.__init__(self, **kwargs)
        self.align = "{:<32} {:<24} {:<12} {:<40}"
        self.columns = ("Name", "Timestamp", "ID", "Value")
        self.color_header = TextColors.CYAN
        self.color_sources = TextColors.BLUE
        self.color_names = TextColors.RED
        self.width = 120
        self.first_record = True

    def center(self, message):
        message_width = len(message)
        if (message_width + 2)< self.width:
            padding = (self.width - message_width) // 2 - 1
            message = '-' * padding + " " + message + " " + '-' * (padding)
        return message

    def print_header(self):
        print(f"{self.color_header}" + self.align.format(*self.columns) + f"{TextColors.RESET}")

    def on_close(self):
        pass

    def on_start(self, source):
        now = timestamp_to_string(utc=False)
        msg = self.center(f"Starting {source.get_desc()} at {now}")
        print(f"{self.color_sources}{msg}{TextColors.RESET}")
        msg = self.center(f"{source.query}")
        print(f"{self.color_sources}{msg}{TextColors.RESET}")

    def on_stop(self, source, exception):
        now = timestamp_to_string(utc=False)
        msg = self.center(f"Finished {source.get_desc()} at {now}")
        print(f"{self.color_sources}{msg}{TextColors.RESET}")

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        #print (f"{self.color_names}\t+{name} - {typ} {byteOrder} {shape} {channel_compression}{TextColors.RESET}")
        pass

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        if self.first_record:
            self.print_header()
            self.first_record = False
        if type(value) == bytes:
            value  = f"bytes({len(value)})"
        elif isinstance(value, np.ndarray) and (len(value.shape) >= 1):
            tokens = str(value).split('\n')
            val_str = tokens[0]
            if len(tokens) > 1:
                val_str = val_str + " ..."
            value = f"{str(value.dtype)}{str(value.shape)} {val_str}"
        else:
            value = str(value)

        if kwargs.get("bins", None):
            value = f"{value}  \t [{kwargs['min']} - {kwargs['max']}]"
        print(self.align.format(
            str(name),
            str(timestamp),
            str(pulse_id),
            value
        ))

    def on_channel_completed(self, source, name):
        #print (f"{self.color_names}\t-{name}{TextColors.RESET}")
        pass


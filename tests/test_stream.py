import time
import unittest
from datahub import *

class Listener (Consumer):
    def on_start(self, source):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        print(f"Started: {name}")

    def on_channel_record(self, source, name, timestamp, pulse_id, value):
        print(f"{timestamp} {name}={str(value)} ")

    def on_channel_completed(self, source, name):
        print(f"Completed: {name}")

    def on_stop(self, source, exception):
        pass


class BsreadTest(unittest.TestCase):

    def test_listeners(self):
        with Bsread(url="tcp://localhost:9999", mode="PULL", time_type="str") as source:
            listener = Listener()
            source.add_listener(listener)
            source.req(["UInt8Scalar", "Float32Scalar"], 0.0, 0.2)

if __name__ == '__main__':
    unittest.main()

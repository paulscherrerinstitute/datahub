import unittest
from datahub import *
import time


class DataBufferTest(unittest.TestCase):

    def test_bsread(self):
        with Stdout() as stdout:
            with Bsread() as bsread:
                bsread.add_listener(stdout)
                bsread.req(["S10BC01-DBPM010:X1", "S10BC01-DBPM010:Q1"], 0.0, 2.0)

    def test_dispatcher(self):
        with Stdout() as stdout:
            with Dispatcher() as dispatcher:
                dispatcher.add_listener(stdout)
                dispatcher.req(["S10BC01-DBPM010:X1", "S10BC01-DBPM010:Q1"], 0.0, 2.0)


if __name__ == '__main__':
    unittest.main()

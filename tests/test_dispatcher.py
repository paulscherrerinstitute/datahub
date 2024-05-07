import unittest
from datahub import *
import time


class DataBufferTest(unittest.TestCase):

    def test_listeners(self):
        with Plot() as plot:
            with Bsread() as source:
                source.add_listener(plot)
                source.req(["S10BC01-DBPM010:X1", "S10BC01-DBPM010:Q1"], 0.0, 2.0)


if __name__ == '__main__':
    unittest.main()

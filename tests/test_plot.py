import time
import unittest
from datahub import *


class PlotTest(unittest.TestCase):

    def test_epics(self):
        with Plot() as plot:
            with Epics(url="localhost:54321", time_type="str") as source:
                source.add_listener(plot)
                source.req(["TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTSINUS2:SinCalc"], 0.0, 4.0)

    def test_camera(self):
        with Plot(max_rate=2.0,) as plot:
             with Camera(url="http://localhost:8888", name="simulation") as source:
                source.add_listener(plot)
                source.req(None, 0.0, 2.0)


    def test_data_buffer(self):
        with Plot() as plot:
             with DataBuffer(time_type="str", ) as source:
                source.add_listener(plot)
                source.req( ["SARFE10-PSSS059:SPECTRUM_Y", "SARFE10-PSSS059:SPECTRUM_X"], "2024-02-14 08:50:00.000", "2024-02-14 08:50:05.000")


    def test_bsread(self):
        with Plot() as plot:
             with Bsread(url="tcp://localhost:9999", mode="PULL", time_type="str", ) as source:
                source.add_listener(plot)
                source.req( ["UInt8Scalar", "Float32Scalar"], 0.0, 2.0, modulo=50)

if __name__ == '__main__':
    unittest.main()

import time
import unittest
from datahub import *


class PlotTest(unittest.TestCase):

    def test_epics(self):
        with PShell(layout ="Vertical", color="GREEN", marker_size=5, line_width=0, max_count=10) as plot:
            with Epics(url="localhost:54321", time_type="sec") as source:
                source.add_listener(plot)
                source.req(["TESTIOC:TESTSINUS:SinCalc"], 0.0, 2.0)

    def test_camera(self):
        with PShell(style="Image", colormap="Flame", max_rate=2.0,marker_size=5, max_count=5) as plot:
             with Camera(url="http://localhost:8888", name="simulation", time_type="sec") as source:
                source.add_listener(plot)
                source.req(None, 0.0, 5.0)


    def test_data_buffer(self):
        with PShell() as plot:
             with DataBuffer(time_type="str", ) as source:
                source.add_listener(plot)
                source.req( ["SARFE10-PSSS059:SPECTRUM_Y", "SARFE10-PSSS059:SPECTRUM_X"], "2024-02-14 08:50:00.000", "2024-02-14 08:50:05.000")


    def test_bsread(self):
        with PShell() as plot:
             with Bsread(url="tcp://localhost:9999", mode="PULL", time_type="str", ) as source:
                source.add_listener(plot)
                source.req( ["UInt8Scalar", "Float32Scalar"], 0.0, 2.0, modulo=50)

if __name__ == '__main__':
    unittest.main()

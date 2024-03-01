import unittest
from datahub import *

url = "tcp://localhost:5554"
filename = "/Users/gobbo_a/dev/back/camserver.h5"
channels = ["intensity", "height"]
start = None
end = 3.0
query = {
    "channels": channels,
    "start": start,
    "end": end,
    "mode": "SUB"
}


url_pipeline_server = "http://localhost:8889"
url_camera_server = "http://localhost:8888"
pipeline = "simulation_sp"
camera = "simulation"

class CamserverTest(unittest.TestCase):
    def setUp(self):
        self.source = Bsread(url=url)
        self.pipeline = Pipeline( url=url_pipeline_server, name=pipeline)
        self.camera = Camera(url=url_camera_server, name=camera)

    def tearDown(self):
        cleanup()

    def test_bsread(self):
        hdf5 = HDF5Writer(filename)
        #stdout = Stdout()
        table = Table()
        self.source.add_listener(hdf5)
        #self.source.add_listener(stdout)
        self.source.add_listener(table)
        self.source.request(query)
        dataframe = table.as_dataframe()
        self.assertEqual(list(dataframe.keys()), channels)
        self.source.close_listeners(True)

    def test_pipeline(self):
        hdf5 = HDF5Writer(filename)
        table = Table()
        self.pipeline.add_listener(hdf5)
        self.pipeline.add_listener(table)
        self.pipeline.request(query)
        dataframe = table.as_dataframe()
        self.assertEqual(list(dataframe.keys()), channels)
        self.pipeline.close_listeners()

    def test_camera(self):
        query["channels"] = None
        hdf5 = HDF5Writer(filename)
        table = Table()
        self.camera.add_listener(hdf5)
        self.camera.add_listener(table)
        self.camera.request(query)
        dataframe = table.as_dataframe()
        self.assertEqual(list(dataframe.keys()), ['width', 'height', 'image', 'x_axis', 'y_axis'])
        self.camera.close_listeners()

if __name__ == '__main__':
    unittest.main()

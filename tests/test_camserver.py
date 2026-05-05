import unittest
from datahub import *

url = "tcp://localhost:5554"
filename = "/Users/gobbo_a/tst.h5"
channels = ["intensity", "height"]
start = None
end = 1.0
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

    def test_pipeline(self):
        #hdf5 = HDF5Writer(filename)
        stdout = Stdout()
        table = Table()
        #self.pipeline.add_listener(hdf5)
        self.pipeline.add_listener(table)
        self.pipeline.add_listener(stdout)
        self.pipeline.request(query)
        dataframe = table.as_dataframe()
        self.assertEqual(list(dataframe.keys()), channels)

    def test_camera(self):
        hdf5 = HDF5Writer(filename)
        table = Table()
        self.camera.add_listener(hdf5)
        self.camera.add_listener(table)
        self.camera.req(channels=None, start=None, end=1.0)
        dataframe = table.as_dataframe()
        self.assertEqual(list(dataframe.keys()), ['width', 'height', 'image', 'x_axis', 'y_axis'])
        print(dataframe)
        self.camera.close_listeners()

    def test_screen_panel(self):
        url = "http://sf-daqsync-01:8889"
        camera = "SATBD02-DSCR050"
        url = "http://localhost:8889"
        camera = "simulation"
        channel = "x_fit_standard_deviation"
        sampling_time = 2.0
        table = Table()
        pipeline = Pipeline(url=url, name=camera+"_sp")
        pipeline.add_listener(table)
        pipeline.req(channels=[channel], start=0.0, end=sampling_time)
        df = table.as_dataframe()
        mean = df[channel].mean()
        print(mean)

    def test_config(self):
        with Pipeline(url=url_pipeline_server, name="[simulation3_sp]", config = {"binning_x":2,"binning_y":2}) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.req(start=0.0, end=2.0, channels=["width", "height"])

        config = {
            "pipeline_type": "processing",
            "camera_name": "simulation"
        }
        with Pipeline(url=url_pipeline_server, config=config) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.request(query)

        with Pipeline(url=url_pipeline_server, name="tst", config=config) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.request(query)

        with Pipeline(url=url_pipeline_server, name=pipeline) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.request(query)

        with Pipeline(url=url_pipeline_server, name="test[simulation3_sp]", config = {"binning_x":2, "binning_y":2}) as source:
            stdout = Stdout()
            source.add_listener(stdout)
            source.req(start = 0.0, end=2.0, channels = ["width", "height"])

    def test_search(self):
        with Pipeline(url=url_pipeline_server) as source:
                print(source.search("SIMU", case_sensitive=False))
        print ("---")
        with Camera(url=url_camera_server) as source:
                print(source.search("SIMU", case_sensitive=False))



    def stop_instance(self, id=None):
        self.get_response("/%s" % self._get_name(id), delete=True)

    def test_camera_config(self):
        with (Camera(url=url_camera_server, name=camera) as cam):
            print(cam.get_info())
            print (cam.get_config_names())
            print (cam.get_instances())
            self.assertEqual(cam.is_active(), True)
            self.assertEqual(cam.is_online(), True)
            print(cam.get_groups())
            cfg = cam.get_config()
            print(cfg)
            cfg2 = cfg.copy()
            cfg2["mirror_x"] = True
            cam.set_config(cfg2)
            self.assertEqual(cam.get_config()["mirror_x"], True)
            cam.set_config_item("mirror_y", True)
            self.assertEqual(cam.get_config()["mirror_y"], True)
            cam.set_config(cfg)
            self.assertEqual(cam.get_config(), cfg)
            print(cam.get_aliases())
            print (cam.search("simu", case_sensitive=False))
            cam.stop_instance()
            print(cam.search("simu", case_sensitive=False))

    def test_camera_config_static(self):
        with (Camera(url=url_camera_server) as cam):
            name = camera
            print(cam.get_info)
            print (cam.get_config_names())
            print (cam.get_instances())
            self.assertEqual(cam.is_active(name), True)
            self.assertEqual(cam.is_online(name), True)
            print(cam.get_groups())
            cfg = cam.get_config(name)
            print(cfg)
            cfg2 = cfg.copy()
            cfg2["mirror_x"] = True
            cam.set_config(cfg2, name)
            self.assertEqual(cam.get_config(name)["mirror_x"], True)
            cam.set_config_item("mirror_y", True, name)
            self.assertEqual(cam.get_config(name)["mirror_y"], True)
            cam.set_config(cfg, name)
            self.assertEqual(cam.get_config(name), cfg)
            print(cam.get_aliases())
            print (cam.search("simu", case_sensitive=False))
            print(cam.search("simu", case_sensitive=False))

    def test_pipeline_config(self):
        with Pipeline( url=url_pipeline_server, name=pipeline) as pip:
            print(pip.get_info())
            print (pip.get_config_names())
            print (pip.get_instances())
            print(pip.get_groups())
            print(pip.get_camera_name())
            print(pip.get_background_name())

            cfg = pip.get_config()
            cfg2 = cfg.copy()
            cfg2["test"] = 1.0
            pip.set_config(cfg2)
            self.assertEqual(pip.get_config()["test"], 1.0)
            pip.set_config_item("test2", "2.0")
            self.assertEqual(pip.get_config()["test2"], "2.0")
            pip.set_config(cfg)
            self.assertEqual(pip.get_config(), cfg)

            cfg = pip.get_instance_config()
            cfg2 = cfg.copy()
            cfg2["image_threshold"] = 100
            pip.set_instance_config(cfg2)
            self.assertEqual(pip.get_instance_config()["image_threshold"], 100)
            pip.set_instance_config_item("image_threshold", 200)
            self.assertEqual(pip.get_instance_config()["image_threshold"], 200)
            pip.set_instance_config(cfg)
            self.assertEqual(pip.get_instance_config(), cfg)

    def test_pipeline_config_static(self):
        with Pipeline( url=url_pipeline_server) as pip:
            name=pipeline
            print(pip.get_info())
            print (pip.get_config_names())
            print (pip.get_instances())
            print(pip.get_groups())
            print(pip.get_camera_name(name))
            print(pip.get_background_name(name))

            cfg = pip.get_config(name)
            cfg2 = cfg.copy()
            cfg2["test"] = 1.0
            pip.set_config(cfg2, name)
            self.assertEqual(pip.get_config(name)["test"], 1.0)
            pip.set_config_item("test2", "2.0", name)
            self.assertEqual(pip.get_config(name)["test2"], "2.0")
            pip.set_config(cfg, name)
            self.assertEqual(pip.get_config(name), cfg)

            cfg = pip.get_instance_config(name)
            cfg2 = cfg.copy()
            cfg2["image_threshold"] = 100
            pip.set_instance_config(cfg2, name)
            self.assertEqual(pip.get_instance_config(name)["image_threshold"], 100)
            pip.set_instance_config_item("image_threshold", 200, name)
            self.assertEqual(pip.get_instance_config(name)["image_threshold"], 200)
            pip.set_instance_config(cfg, name)
            self.assertEqual(pip.get_instance_config(name), cfg)

    def test_pipeline_backgroung(self):
        with Pipeline( url=url_pipeline_server, name=pipeline) as pip:
            print (pip.get_background_name())
            print(pip.get_backgrounds())
            print(pip.get_latest_background())
            print(pip.get_background(pip.get_latest_background()).shape)
            print(pip.collect_background(n_images=5))



if __name__ == '__main__':
    unittest.main()

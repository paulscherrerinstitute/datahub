import logging
import sys
import numpy as np
from datahub import Consumer
from datahub.utils.timing import string_to_timestamp

_logger = logging.getLogger(__name__)

def import_dynamic():
    import importlib.util
    import urllib.request
    module_name = 'pshell_plot'
    module_url = 'https://raw.githubusercontent.com/paulscherrerinstitute/pshell/master/src/main/python/pshell/plot.py'
    response = urllib.request.urlopen(module_url)
    module_code = response.read()
    module_spec = importlib.util.spec_from_loader(module_name, loader=None, origin=module_url)
    module = importlib.util.module_from_spec(module_spec)
    module.__file__ = module_url
    exec(module_code, module.__dict__)
    sys.modules[module_name] = module

try:
    from pshell.plot import PlotClient
except:
        PlotClient = None



class PShell(Consumer):
    def __init__(self,  channels=None, address="localhost", port=7777, timeout=3.0, layout="Vertical", context=None,  **kwargs):
        global PlotClient
        Consumer.__init__(self, **kwargs)
        self.clients = {}
        self.plots = {}
        self.address = address
        self.port = port
        self.timeout = timeout
        self.channels = channels
        self.layout = layout
        self.context = context

        if PlotClient is None:
            # If PShell package not installed try to load the plot client from the URL
            try:
                import_dynamic()
                import pshell_plot
                PlotClient = pshell_plot.PlotClient
            except:
                raise "Cannot import PShell plotting library"

        ps = PlotClient(address=self.address, port=self.port,  timeout=self.timeout)
        try:
            ps.get_contexts()
        except:
            raise Exception("Cannot connect to plot server on port " + str(self.port))
        finally:
            ps.close()

    def on_close(self):
        for name, client in self.clients.items():
            client.close()

    def on_start(self, source):
        pc = PlotClient(address=self.address, port=self.port, context=self.context, timeout=self.timeout)
        self.clients[source] = pc
        pc.clear_plots()
        pc.set_context_attrs(quality=None, layout=self.layout)
        pc.set_progress(None)
        pc.set_status("Idle")

    def on_stop(self, source, exception):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        if self.channels:
            if not name in self.channels:
                return
        pc = self.clients[source]
        if len(shape)==0:
            plot = pc.add_line_plot(name)
            pc.clear_plot(plot)
            series = pc.add_line_series(plot, name)
            pc.set_line_series_attrs(series, color=None, marker_size=3, line_width=None, max_count=None)
            xdata = None
        elif len(shape) == 1:
            plot = pc.add_line_plot(name)
            pc.clear_plot(plot)
            series = pc.add_line_series(plot, name)
            pc.set_line_series_attrs(series, color=None, marker_size=1, line_width=None, max_count=None)
            xdata = list(range(shape[0]))
        elif len(shape) == 2:
            plot = pc.add_matrix_plot(name, style=None, colormap="Viridis")
            series = pc.add_matrix_series(plot, "Matrix Series 1")
            pc.set_matrix_series_attrs(series, None, None, None, None, None, None)
            xdata = None
        else:
            _logger.warning("Unsupported shape for channel: " + name)
            return
        pc.clear_series(series)
        self.plots[name] = (plot, series, shape, xdata)
        pc.set_status("Running")
        pc.set_progress(0.5)

    def on_channel_record(self, source, name, timestamp, pulse_id, value):
        if name in self.plots:
            plot, series, shape, xdata = self.plots[name]
            pc = self.clients[source]
            try:
                if len(shape) == 0:
                    if type(timestamp) == str:
                        timestamp = string_to_timestamp(timestamp)
                    if isinstance(value, np.floating):  # Different scalar float types don't change header
                        value = float(value)
                    if isinstance(value, np.integer):  # Different scalar int types don't change header
                        value = int(value)
                    pc.append_line_series_data(series, timestamp, value, None)
                elif len(shape) == 1:
                    pc.set_line_series_data(series, xdata, value.tolist(),  None)
                elif len(shape) == 2:
                    pc.set_matrix_series_data(series, value.tolist(), None, None)
            except Exception as e:
                print("Error in plotting: " + str(e))


    def on_channel_completed(self, source, name):
        pc = self.clients.get(source, None)
        if pc:
            pc.set_progress(None)
            pc.set_status("Done")





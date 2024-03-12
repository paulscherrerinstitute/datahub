import logging
import sys
import traceback

import numpy as np
from datahub import Consumer
from datahub.utils.timing import string_to_timestamp, convert_timestamp
import multiprocessing
import time

_logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
except:
    plt = None

plots = {}


def is_notebook():
    return plt.get_backend() in ["nbAgg", "backend_interagg", "module://backend_interagg"]

def create_plot(name, shape, typ, xdata, start):
    try:
        global plots
        if len(shape) == 0:
            fig, ax = plt.subplots(num=name)
            ax.set_title(name)
            plot, = ax.plot([], [], marker='o')
            # ax.set_xlim(0, 10)
            # ax.set_ylim(0, 100)
        elif len(shape) == 1:
            fig, ax = plt.subplots(num=name)
            ax.set_title(name)
            plot, = ax.plot([], [], marker='.')
            plot.set_xdata(xdata)
        elif len(shape) == 2:
            image_data = np.zeros(shape, typ)
            fig, ax = plt.subplots(num=name)
            plot = ax.imshow(image_data, cmap='viridis', origin='lower')
        else:
            return
        if not is_notebook():
            plt.ion()  # Turn on interactive mode
            plt.show()  # Display the current subplot


        plots[name] = (plot, shape, fig, ax)
    except Exception as ex:
        print(f"Exception creating {name}: {str(ex)}")
        traceback.print_exc()


def update_plot(name, timestamp, value):
    try:
        if name in plots:
            (plot, shape, fig, ax) = plots[name]
            if plot is not None:
                if len(shape) == 0:
                    plot.set_xdata(np.append(plot.get_xdata(), timestamp))
                    plot.set_ydata(np.append(plot.get_ydata(), value))
                    ax.relim()  # Recalculate the data limits
                    ax.autoscale_view()  # Autoscale the view based on the data limits
                elif len(shape) == 1:
                    plot.set_ydata(value)
                    ax.relim()  # Recalculate the data limits
                    ax.autoscale_view()  # Autoscale the view based on the data limits
                else:
                    plot.set_array(value)
                    plot.norm = plt.Normalize(value.min(), value.max())
                    plt.draw()
            if not is_notebook():
                plt.pause(0.01)

    except Exception as ex:
        print(f"Exception adding to {name}: {str(ex)}")
        traceback.print_exc()

def show_plot(name):
    if name in plots:
        del plots[name]
        if len(plots) == 0:
            try:
                #plt.ioff()  # Turn off interactive mode
                #plt.show(block=False)
                pass
            except:
                pass

def get_open_figures():
    open_figures = [fig for fig in plt._pylab_helpers.Gcf.get_all_fig_managers() if
                    fig.canvas.figure.stale is False]
    return len(open_figures)


def process_plotting(tx_queue,  stop_event):
    _logger.info("Start plotting process")
    stop_event.clear()
    try:
        while not stop_event.is_set():
            try:
                tx= tx_queue.get(False)
            except:
                if get_open_figures() > 0:
                    plt.pause(0.01)
                else:
                    time.sleep(0.01)
                continue
            if tx is not None:
                if tx[0] == "START":
                    create_plot(*tx[1:])
                elif tx[0] == "REC":
                    update_plot(*tx[1:])
                elif tx[0] == "END":
                    show_plot(*tx[1:])
    except Exception as e:
        _logger.exception(e)
    finally:
        stop_event.set()
        if is_notebook():
            plt.show()
        else:
            while get_open_figures() > 0:
                plt.pause(0.1)
        _logger.info("Exit plotting process")
        sys.exit(0)


class Plot(Consumer):
    def __init__(self,  channels=None, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.plots = {}
        self.channels = channels

        if plt is None:
            raise "Cannot import matplotlib"

        self.tx_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.stop_event.set()
        self.plotting_process = multiprocessing.Process(target=process_plotting, args=(self.tx_queue, self.stop_event))
        self.plotting_process.start()
        #Wait process to start
        start = time.time()
        while self.stop_event.is_set():
            if time.time() - start > 5.0:
                raise "Cannot start plotting process"
            time.sleep(0.01)


    def on_close(self):
        while not self.tx_queue.empty():
            time.sleep(0.1)
        self.stop_event.set()
        self.plots = {}
        self.tx_queue.close()


    def on_start(self, source):
        pass

    def on_stop(self, source, exception):
        pass

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        if self.channels:
            if not name in self.channels:
                return
        if len(shape)==0:
            xdata = None
        elif len(shape) == 1:
            xdata = list(range(shape[0]))
        elif len(shape) == 2:
            xdata = None
        else:
            _logger.warning("Unsupported shape for channel: " + name)
            return
        self.tx_queue.put(["START", name, shape, typ, xdata, time.time()])
        self.plots[name] = [shape, xdata, time.time()]
        time.sleep(0.1)

    def on_channel_record(self, source, name, timestamp, pulse_id, value):
        if name in self.plots:
            shape, xdata, start = self.plots[name]
            try:
                if type(timestamp) == str:
                    timestamp = string_to_timestamp(timestamp)
                if type(timestamp) == int:
                    timestamp = float(timestamp)/10e9
                if isinstance(value, np.floating):  # Different scalar float types don't change header
                    value = float(value)
                if isinstance(value, np.integer):  # Different scalar int types don't change header
                    value = int(value)
                timestamp = timestamp - start
                self.tx_queue.put(["REC", name, timestamp, value])
                #time.sleep(0.1)
            except Exception as e:
                print("Error in plotting: " + str(e))



    def on_channel_completed(self, source, name):
        self.tx_queue.put(["END", name])





import logging
import sys
import traceback

import numpy as np
from datahub import Consumer
from datahub.utils.timing import string_to_timestamp, convert_timestamp
import multiprocessing
import time

_logger = logging.getLogger(__name__)


plt = None
def import_plplot():
    global plt
    try:
        import matplotlib.pyplot
        plt =  matplotlib.pyplot
    except:
        raise Exception("Cannot import matplotlib")

plots = {}


def is_notebook():
    return plt.get_backend() in ["nbAgg", "backend_interagg", "module://backend_interagg"]

def create_plot(name, shape, typ, xdata, start, colormap, color, marker_size, line_width, max_count):
    try:
        global plots
        if len(shape) == 0:
            fig, ax = plt.subplots(num=name)
            ax.set_title(name)
            plot, = ax.plot([], [], marker='o', color=color, markersize=marker_size, linewidth=line_width)
            # ax.set_xlim(0, 10)
            # ax.set_ylim(0, 100)
        elif len(shape) == 1:
            fig, ax = plt.subplots(num=name)
            ax.set_title(name)
            plot, = ax.plot([], [], marker='.', color=color)
            plot.set_xdata(xdata)
        elif len(shape) == 2:
            image_data = np.zeros(shape, typ)
            fig, ax = plt.subplots(num=name)
            plot = ax.imshow(image_data, cmap=colormap, origin='lower')
        else:
            return
        if not is_notebook():
            plt.ion()  # Turn on interactive mode
            plt.show()  # Display the current subplot


        plots[name] = (plot, shape, fig, ax, max_count)
    except Exception as ex:
        print(f"Exception creating {name}: {str(ex)}")
        traceback.print_exc()


def update_plot(name, timestamp, value):
    try:
        if name in plots:
            (plot, shape, fig, ax, max_count) = plots[name]
            if plot is not None:
                if len(shape) == 0:
                    x, y = np.append(plot.get_xdata(), timestamp), np.append(plot.get_ydata(), value)
                    if max_count:
                        if len(x) > max_count:
                            x, y = x[-max_count:], y[-max_count:]

                    plot.set_xdata(x)
                    plot.set_ydata(y)
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
                repaint(0.01)

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
    open_figures = [fig for fig in plt._pylab_helpers.Gcf.get_all_fig_managers()]
    return len(open_figures)


def process_plotting(tx_queue,  stop_event):
    _logger.info("Start plotting process")
    stop_event.clear()
    import_plplot()
    try:
        while not stop_event.is_set():
            try:
                tx= tx_queue.get(False)
            except:
                repaint(0.01)
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
                repaint()

        _logger.info("Exit plotting process")
        sys.exit(0)


def repaint(interval=0.1, show_plot=False):
    if get_open_figures() > 0:
        #plt.pause(interval)

        #Doing this instead of calling pause in order multiple windows not to fliker
        manager = plt.get_current_fig_manager()
        if manager is not None:
            canvas = manager.canvas
            if canvas.figure.stale:
                canvas.draw_idle()
            if show_plot:
               plt.show(block=False)
            canvas.start_event_loop(interval)
            return
    time.sleep(interval)

class Plot(Consumer):
    def __init__(self,  channels=None, colormap="viridis", color=None,  marker_size=None, line_width=None, max_count=None, max_rate=None, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.plots = {}
        self.channels = channels
        self.min_interval = (1.0/max_rate) if max_rate else None
        self.last_plotted_record={}
        self.colormap = colormap.lower() if colormap else None
        self.color = color
        self.marker_size= marker_size
        self.line_width = line_width
        self.max_count = int(max_count) if max_count else None

        import_plplot()

        self.tx_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.stop_event.set()
        self.plotting_process = multiprocessing.Process(target=process_plotting, args=(self.tx_queue, self.stop_event))
        self.plotting_process.start()
        #Wait process to start
        start = time.time()
        while self.stop_event.is_set():
            if time.time() - start > 5.0:
                raise Exception("Cannot start plotting process")
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
        self.tx_queue.put(["START", name, shape, typ, xdata, time.time(), self.colormap, self.color, self.marker_size, self.line_width, self.max_count])
        self.plots[name] = [shape, xdata, time.time()]
        time.sleep(0.1)

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        if name in self.plots:
            shape, xdata, start = self.plots[name]
            try:
                if self.min_interval:
                    if len(shape) > 0: #Only downsample arrays
                        timespan = time.time() - self.last_plotted_record.get(name, 0.0)
                        if timespan < self.min_interval:
                            return
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
                if self.min_interval:
                    self.last_plotted_record[name] = time.time()
                #time.sleep(0.1)
            except Exception as e:
                print("Error in plotting: " + str(e))



    def on_channel_completed(self, source, name):
        self.tx_queue.put(["END", name])





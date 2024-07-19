import logging
import time
from datahub.utils.data import *
from datahub.utils.checker import check_msg
from datahub.utils.timing import get_utc_offset, string_to_timestamp, time_to_pulse_id

_logger = logging.getLogger(__name__)

class Align():
    def __init__(self, callback,  channels=None, range=None, filter=None, partial_msg=True, size_buffer=1000, utc_timestamp=False):
        self.set_channels(channels)
        self.size_buffer = size_buffer
        self.aligned_data = MaxLenDict(maxlen=int(size_buffer*1.2))
        self.partial_msg=partial_msg
        self.on_msg=callback
        self.range = range
        self.filter = filter
        self.sent_id = -1
        self.utc_offset = get_utc_offset() if utc_timestamp else 0

    def set_channels(self, channels):
        self.channels = channels
        self.no_channels = 0 if channels==None else len(channels)

    def add(self, id, timestamp, channel, value):
        if not id:
            id = time_to_pulse_id(timestamp)
        if id not in self.aligned_data:
            self.aligned_data[id] = {"timestamp": timestamp}
        self.aligned_data[id][channel] = value

    def reset(self):
        self.aligned_data.clear()

    def set_range(self, range):
        self.range = range

    def set_filter(self, filter):
        self.filter = filter

    def process(self):
        keys_in_order = sorted(list(self.aligned_data.keys()))
        last_complete_id = -1
        for id in [keys_in_order[i] for i in range(len(keys_in_order) - 1, 0, -1)]:
            if len(self.aligned_data[id]) == (self.no_channels + 1):
                last_complete_id = id
                break

        for i in range(len(keys_in_order)):
            id = keys_in_order[i]
            complete = len(self.aligned_data[id]) == (self.no_channels + 1)
            done = complete or (last_complete_id > id) or (len(self.aligned_data) > self.size_buffer)
            if not done:
                break
            msg = self.aligned_data.pop(id)
            if complete or self.partial_msg:
                if self.sent_id >= id:
                    _logger.warning(f"Invalid ID {id} - last sent ID {self.sent_id}")
                else:
                    timestamp = msg.pop("timestamp", None)
                    started = True
                    if self.range:
                        if isinstance(timestamp, str):
                            timestamp_s = string_to_timestamp(timestamp)
                        else:
                            timestamp_s = timestamp/1e9 if isinstance(timestamp, int) else timestamp
                        timestamp_s = timestamp_s + self.utc_offset if timestamp_s else time.time()
                        started = self.range.has_started(timestamp_s)
                    if started:
                        try:
                            if not self.filter or self.is_valid(self.filter, id, timestamp, msg):
                                self.on_msg(id, timestamp, msg)
                        except Exception as e:
                            _logger.exception("Error receiving data: %s " % str(e))
                    self.sent_id = id
            else:
                logging.debug(f"Discarding partial message: {id}")

    def is_valid(self, filter, id, timestamp, msg):
        try:
            return check_msg(msg, filter)
        except Exception as e:
            _logger.warning("Error processing filter: %s " % str(e))
            return False
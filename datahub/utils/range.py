import sys
import time

from datahub import is_null_str
from datahub.utils.timing import *

_logger = logging.getLogger(__name__)

class QueryRange():
    """
    The query range is defined by the parameters "start" and "end" in the parameters.
    If  type is float or float-convertible string, it means the time in seconds since the epoch, or
        if the value is lesser than max_relative_time, an offest to current epoch.
    If type is an int or int-convertible string, it means an id or
        if the value is lesser than max_relative_is, an offset to current id`.
    If type is str it is a date in ISO format.

    Optionally parameters "start_id", end_id", "start_tm" and end_tm" can be used to avoid type errors,
    """
    RANGE_DEFAULTS_PULSE_ID = -(5 * 365 * 24 * 3600), (365 * 24 * 3600)  #From 5 years ago to one year from now

    def __init__(self, query, source=None):
        now = time.time()
        self.start = self._check_str(query.get("start", None))
        self.end = self._check_str(query.get("end", None))
        self.source = source
        range_defaults_pulse_id = self.time_to_id(now + QueryRange.RANGE_DEFAULTS_PULSE_ID[0]), \
                                  self.time_to_id(now + QueryRange.RANGE_DEFAULTS_PULSE_ID[1])
        if type(self.start) == float: #timestamp
            if range_defaults_pulse_id[0] < self.start <range_defaults_pulse_id[1]:
                self.start = int(self.start) #assumes pulse id
        if type(self.end) == float: #timestamp
            if range_defaults_pulse_id[0] < self.end <range_defaults_pulse_id[1]:
                self.end = int(self.end) #assumes pulse id

        start_id = query.get("start_id", None)
        if start_id is not None:
            self.start = int(start_id)
        end_id = query.get("end_id", None)
        if end_id is not None:
            self.end = int(end_id)

        start_tm = self._check_str(query.get("start_tm", None))
        if start_tm is not None:
            self.start = float(start_tm)
        end_tm = self._check_str(query.get("end_tm", None))
        if end_tm is not None:
            self.end = end_tm if (type(end_tm) == str) else float(end_tm)

        if self.start is None:
            if type(self.end) == int:
                self.start = 0
            elif type(self.end) == str:
                self.start = self.seconds_to_string(now)
            else:
                self.start = 0.0
        if self.end is None:
            if type(self.start) == int:
                self.end = 0
            elif type(self.start) == str:
                self.end = self.seconds_to_string(now)
            else:
                self.end = 0.0
        #import pytz
        #self.utc_tz = pytz.utc
        #self.local_tz = pytz.timezone('Europe/Zurich')
        self.max_relative_time = 1000000.0 #in secs ~=11 days
        self.max_relative_id = 100000000

        #Seconds
        self.start_sec, self.start_str, self.start_id, self.start_type = self._parse_par(self.start, now, True)
        self.end_sec, self.end_str, self.end_id, self.end_type = self._parse_par(self.end, now, False)

        if self.start_sec > self.end_sec:
            raise Exception("Invalid query range: %s to %s" % (self.start, self.end))

    def _check_str(self, par):
        if type(par) == str:
            try:
                return float(par)
            except:
                try:
                    return int(par)
                except:
                    if is_null_str(par):
                        return None
                    return par
        return par

    def _parse_par(self, par, now, start):
        if par is None: #Absent parameters mean the current time
            par = 0.0
        if type(par) == float:
            sec = par
            if par <= self.max_relative_time:
                sec = sec + now
            st = self.seconds_to_string(sec)
            id = None
            typ = "time"
        #Date
        elif type(par) == str:
            sec = self.string_to_seconds(par)
            st = par
            id = None
            typ = "date"
        #ID
        elif type(par) == int:
            id = par
            if par <= self.max_relative_id:
                id = id + self.time_to_id()
            sec = self.id_to_time(id)
            offset = PULSE_ID_INTERVAL/2
            sec = sec + (-offset if start else offset)
            st = self.seconds_to_string(sec)
            typ = "id"
        else:
            raise Exception("Invalid parameter value: " + str(par))
        return sec, st, id, typ

    def time_to_id(self, tm=time.time()):
        if self.source is not None:
            return self.source.time_to_pulse_id(tm)
        return time_to_pulse_id(tm)

    def id_to_time(self, id):
        if self.source is not None:
            return self.source.pulse_id_to_time(id)
        return pulse_id_to_time(id)

    def wait_time(self, target_time):
        current_time = time.time()
        while current_time < target_time:
            time.sleep(target_time - current_time)
            current_time = time.time()

    def wait_start(self, delay=0.0):
        self.wait_time(self.get_start_sec() + delay)

    def wait_end(self, delay=0.0):
        self.wait_time(self.get_end_sec() + delay)

    def has_started(self, tm=None):
        if tm is None:
            tm = time.time()
        return tm >= self.get_start_sec()

    def has_ended(self, tm=None):
        if tm is None:
            tm = time.time()
        return tm > self.get_end_sec()

    def is_running(self, tm=None):
        if tm is None:
            tm = time.time()
        return self.has_started(tm) and not self.has_ended(tm)

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    def get_start_sec(self):
        return self.start_sec

    def get_end_sec(self):
        return self.end_sec

    def get_start_str(self):
        return self.start_str

    def get_end_str(self):
        return self.end_str

    def get_start_str_iso(self):
        start = self.get_start_str()
        start = self.string_to_datetime(start)
        return datetime.isoformat(start)

    def get_end_str_iso(self):
        end = self.get_end_str()
        end = self.string_to_datetime(end)
        return datetime.isoformat(end)

    def get_start_id(self):
        return self.start_id

    def get_end_id(self):
        return self.end_id

    def get_start_type(self):
        return self.start_type

    def get_end_type(self):
        return self.end_type

    def get_type(self):
        return self.get_end_type()

    def is_start_by_id(self):
        return self.start_id is not None

    def is_end_by_id(self):
        return self.end_id is not None

    def seconds_to_string(self, seconds, utc=True):
        return timestamp_to_string(seconds, utc)

    def string_to_seconds(self, date_string):
        return string_to_timestamp(date_string)

    def string_to_datetime(self, date_string):
        if isinstance(date_string, str):
            date = string_to_datetime(date_string)
        elif isinstance(date_string, datetime.datetime):
            date = date_string
        else:
            raise ValueError("Unsupported date type: " + type(date_string))
        if date.tzinfo is None:  # localize time if necessary
            try:
                import pytz
                date = pytz.timezone('Europe/Zurich').localize(date)
            except Exception as ex:
                _logger.error(ex)
        return date

    def __str__(self):
       return f"Range from {self.get_start_str()} ({self.get_start_id()}) to {self.get_end_str()} ({self.get_end_id()})"


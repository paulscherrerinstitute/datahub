import time
import datetime
import logging
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)
try:
    from dateutil import parser as dateutil_parser
except:
    _logger.error("dateutil not installed: fewer data formats are supported")
    dateutil_parser=None

PULSE_ID_START_TIME = 1504951960.114 # This  is fluctuating and changed after Jul/24 from 1504531686.91
PULSE_ID_INTERVAL = 0.01
PULSE_ID_INTERVAL_DEC = len(str(PULSE_ID_INTERVAL).split('.')[1]) if '.' in str(PULSE_ID_INTERVAL) else 0

def create_timestamp(sec, nano=0):
    #Doing in 2 steps, because if multiply by 10e9 that there will rounding error that will change the final timestamp
    micros = int(sec * 1000000)
    return (micros * 1000) + nano

def adjust_time_type(type):
    if type is not None:
        if type.lower() in ["str", "string"]:
            return "str"
        elif type.lower()in ["sec", "secs", "seconds"]:
            return "sec"
        elif type.lower() in ["milli", "millis", "milliseconds"]:
            return "milli"
        else:
            return "nano"

def convert_timestamp(timestamp, type="nano", from_type=None):
    if timestamp:
        if type:
            if not type:
                if type(timestamp)==str:
                    from_type = "str"
                elif type(timestamp) == float:
                    from_type = "sec"
                elif timestamp < 100000000000000:
                    from_type = "millis"
                else:
                    from_type ="nano"
            if type != from_type:
                if from_type == "str":
                    timestamp = string_to_timestamp(timestamp)
                    from_type = "sec"
                if from_type == "nano":
                    if type == "str":
                        secs = float(timestamp) / 1000000000.0
                        return timestamp_to_string(secs, False)[:-3]
                    elif type == "sec":
                        return float(timestamp) / 1000000000.0
                    elif type == "milli":
                        return int(timestamp/1000000)
                elif from_type == "milli":
                    if type == "str":
                        secs = float(timestamp) / 1000.0
                        return timestamp_to_string(secs, False)[:-3]
                    elif type =="sec":
                        return float(timestamp) / 1000.0
                    elif type =="nano":
                        return int(timestamp * 1000000)
                elif from_type == "sec":
                    if type == "str":
                        return timestamp_to_string(timestamp , False)[:-3]
                    elif type == "milli":
                        return float(timestamp) * 1000.0
                    elif type == "nano":
                        return int(timestamp * 1000000000)
    return timestamp

def time_to_pulse_id(tm=None):
    if not tm:
        tm = time.time()
    tm = tm - get_utc_offset()
    offset = tm - PULSE_ID_START_TIME
    pid = int(offset / PULSE_ID_INTERVAL)
    return pid

def pulse_id_to_time(id):
    offset = float(id) * PULSE_ID_INTERVAL
    ret = PULSE_ID_START_TIME + offset
    ret = ret + get_utc_offset()
    return round(ret, PULSE_ID_INTERVAL_DEC)


def timestamp_to_string(seconds=None, utc=True):
    if not seconds:
        seconds = time.time()
    if utc:
        dt = datetime.utcfromtimestamp(seconds)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f') + 'Z'
    else:
        dt = datetime.fromtimestamp(seconds)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')

def string_to_timestamp(date_string):
    dt = string_to_datetime(date_string)
    return dt.timestamp()

def string_to_datetime(date_string):
    if dateutil_parser:
        return dateutil_parser.parse(date_string)
    else:
        return datetime.fromisoformat(date_string.rstrip('Z')).replace(tzinfo=timezone.utc)

def get_utc_offset():
    now = time.time()
    dt_utc = datetime.utcfromtimestamp(now)
    dt_local = datetime.fromtimestamp(now)
    difference = dt_local-dt_utc
    return difference.total_seconds()
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

def convert_timestamp(timestamp, type="nano"):
    if type == "str":
        secs = float(timestamp) / 1000000000.0
        return timestamp_to_string(secs, False)[:-3]
    elif type =="sec":
        return float(timestamp) / 1000000000.0
    elif type =="milli":
        return int(timestamp/1000000)
    return timestamp

def time_to_pulse_id(tm=time.time()):
    tm = tm - get_utc_offset()
    offset = tm - PULSE_ID_START_TIME
    id = int(offset / PULSE_ID_INTERVAL)
    return id

def pulse_id_to_time(id):
    offset = float(id) * PULSE_ID_INTERVAL
    ret = PULSE_ID_START_TIME + offset
    ret = ret + get_utc_offset()
    return round(ret, PULSE_ID_INTERVAL_DEC)


def timestamp_to_string(seconds=time.time(), utc=True):
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
########################################################################################################################
# HTTP Utilities
########################################################################################################################

import datahub
import json
import http
import ssl
import urllib
import re
import sys
import logging

_logger = logging.getLogger(__name__)

def get_host_port_from_stream_address(stream_address):
    if stream_address.startswith("ipc"):
        return stream_address.split("//")[1], -1
    source_host, source_port = stream_address.rsplit(":", maxsplit=1)
    source_host = source_host.split("//")[1]
    return source_host, int(source_port)

def create_http_conn(up):
    if up.scheme == "https":
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ctx.check_hostname = False
        port = up.port
        if port is None:
            port = 443
        conn = http.client.HTTPSConnection(up.hostname, port, context=ctx)
    else:
        port = up.port
        if port is None:
            port = 80
        conn = http.client.HTTPConnection(up.hostname, port)
    return conn


def http_req(method, url):
    headers = {
        "X-PythonDataAPIPackageVersion": datahub.version(),
        "X-PythonDataAPIModule": __name__,
        "X-PythonVersion": re.sub(r"[\t\n]", " ", str(sys.version)),
        "X-PythonVersionInfo": str(sys.version_info),
    }
    up = urllib.parse.urlparse(url)
    conn = create_http_conn(up)
    conn.request(method, up.path, None, headers)
    #return conn.getresponse()
    return conn


def http_data_query(query, url):
    method = "POST"
    body = json.dumps(query)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
        "X-PythonDataAPIPackageVersion": datahub.version(),
        "X-PythonDataAPIModule": __name__,
        "X-PythonVersion": re.sub(r"[\t\n]", " ", str(sys.version)),
        "X-PythonVersionInfo": str(sys.version_info),
    }
    up = urllib.parse.urlparse(url)
    conn = create_http_conn(up)
    conn.request(method, up.path, body, headers)
    #return conn.getresponse()
    return conn

def get_json(url):
    conn = http_req("GET", url)
    try:
        res = conn.getresponse()
        body = res.read().decode()
        try:
            return json.loads(body)
        except:
            _logger.error(f"can not parse request status as json\n" + body)
            return body
    finally:
        conn.close()

def save_raw(query, url, fname):
    conn = http_data_query(query, url)
    try:
        s = conn.getresponse()
        with open(fname, "wb") as f1:
            while True:
                buf = s.read()
                if buf is None:
                    break
                if len(buf) < 0:
                    raise RuntimeError()
                if len(buf) == 0:
                    break
                f1.write(buf)
    finally:
        conn.close()


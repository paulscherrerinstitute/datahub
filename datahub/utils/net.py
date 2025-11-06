########################################################################################################################
# HTTP Utilities
########################################################################################################################

import datahub
import json
from http.client import HTTPSConnection, HTTPConnection
import ssl
import urllib
import re
import sys
import logging
import socket
import io
import zlib
import gzip

_logger = logging.getLogger(__name__)

def get_host_port_from_stream_address(stream_address):
    if stream_address.startswith("ipc"):
        return stream_address.split("//")[1], -1
    source_host, source_port = stream_address.rsplit(":", maxsplit=1)
    if "//" in source_host:
        source_host = source_host.split("//")[1]
    return source_host, int(source_port)

def create_http_conn(up, timeout=None):
    if type(up) == str:
        up = urllib.parse.urlparse(up)
    if timeout is None:
        timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    if up.scheme == "https":
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ctx.check_hostname = False
        port = up.port
        if port is None:
            port = 443
        conn = HTTPSConnection(up.hostname, port, context=ctx, timeout=timeout)
    else:
        port = up.port
        if port is None:
            port = 80
        conn = HTTPConnection(up.hostname, port, timeout=timeout)
    return conn


def http_req(method, url, conn=None, timeout=None):
    headers = {
        "X-PythonDataAPIPackageVersion": datahub.version(),
        "X-PythonDataAPIModule": __name__,
        "X-PythonVersion": re.sub(r"[\t\n]", " ", str(sys.version)),
        "X-PythonVersionInfo": str(sys.version_info),
    }
    up = urllib.parse.urlparse(url)
    if conn is None:
        conn = create_http_conn(up, timeout)
    conn.request(method, up.path, None, headers)
    #return conn.getresponse()
    return conn



def get_default_header(compression=False):
    ret = {   "User-Agent": datahub.package_name(),
               "Accept": "*/*",
               "Content-Type": "application/json",
               "Connection": "keep-alive",
            }
    return ret


def http_data_query(query, url, method = "POST", content_type="application/json", accept="application/octet-stream",
                    add_headers={}, accept_comppression=None, conn=None, timeout=None):
    headers = get_default_header()
    headers["Content-Type"] = content_type
    headers["Accept"] = accept
    if accept_comppression:
        headers["Accept-Encoding"] = "gzip, deflate" if accept_comppression==True else accept_comppression
    headers.update(add_headers)

    up = urllib.parse.urlparse(url)
    if conn is None:
        conn = create_http_conn(up, timeout)
    if method == "GET":
        params = urllib.parse.urlencode(query)
        url = f'{url}?{params}'
        conn.request("GET", url, headers=headers)
    else:
        body = json.dumps(query)
        conn.request(method, up.path, body, headers)
    return conn


def check_compression(response):
    encoding = response.getheader("Content-Encoding")
    if encoding == "gzip":
        return gzip.GzipFile(fileobj=response)
    elif encoding == "deflate":
        #return io.BytesIO(zlib.decompress(response.read())) #This reads all the stream upfront
        return DeflateReader(response)
    else:
        return response

def get_json(url, timeout=None):
    conn = http_req("GET", url, timeout=timeout)
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

def save_raw(query, url, fname, timeout=None):
    conn = http_data_query(query, url, timeout)
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

class DeflateReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.decompressor = zlib.decompressobj()
        self.buffer = b""

    def read(self, size=-1):
        while len(self.buffer) < size or size < 0:
            chunk = self.stream.read(8192)
            if not chunk:
                self.buffer += self.decompressor.flush()
                break
            self.buffer += self.decompressor.decompress(chunk)

        if size < 0:
            data, self.buffer = self.buffer, b""
        else:
            data, self.buffer = self.buffer[:size], self.buffer[size:]
        return data
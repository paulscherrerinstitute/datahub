from datahub import *

try:
    import redis
except:
    redis = None


try:
    import websockets
except:
    websockets = None
import asyncio
import json
import threading
import time

_logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, uri):
        if websockets is None:
            raise Exception("Websockets library not available")
        self.uri = uri
        self.loop = asyncio.new_event_loop()
        self.websocket = None
        self.status = {}
        self.last_status_update_time = 0
        self.receive_thread = threading.Thread(target=self._run_loop, daemon=True)

    def start(self):
        self.receive_thread.start()
        # Wait until websocket is connected
        while self.websocket is None and self.receive_thread.is_alive():
            time.sleep(0.1)
        self.wait_status_update()

    def _run_loop(self):
        try:
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._connect_and_receive())
        except Exception as e:
            _logger.exception(e)

    async def _connect_and_receive(self):
        async with websockets.connect(self.uri) as ws:
            self.websocket = ws
            try:
                async for message in ws:
                    try:
                        data = json.loads(message)
                        _logger.debug(f"<<< Received: {data}")
                        self.status = data  # Update status attribute
                        self.last_status_update_time = time.time()
                    except json.JSONDecodeError:
                        _logger.debug(f"<<< Received non-JSON: {message}")
                        pass
            except websockets.exceptions.ConnectionClosed:
                _logger.debug("Connection closed.")
                pass

    async def close_websocket(self):
        if self.websocket is not None:
            await self.websocket.close()

    def wait_status_update(self, timeout = 3.0):
        start_time = time.time()
        last_status_update_time = self.last_status_update_time
        while last_status_update_time == self.last_status_update_time:
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.01)
        return True

    def send_command(self, command_dict):
        if self.websocket is None:
            raise Exception("WebSocket not connected")

        message = json.dumps(command_dict)
        asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)
        _logger.info(f">>> Sent: {message}")
        self.wait_status_update()

    def send_stop(self):
        self.send_command({"command": "stop"})

    def send_start(self,start_id, end_id):
        self.send_command({
            "command": "start",
            "start_image_id": start_id,
            "end_image_id": end_id
        })

    def close(self):
        if self.websocket is not None:
            # Schedule graceful close of websocket
            fut = asyncio.run_coroutine_threadsafe(self.close_websocket(), self.loop)
            try:
                fut.result(timeout=2)  # wait for proper close
            except Exception as e:
                _logger.warning(f"WebSocket close timeout or error: {e}")
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.receive_thread.join()

    def get_status(self, wait_new=False):
        if wait_new:
            self.wait_status_update()
        try:
            return str(self.status["status"])
        except:
            return "unknown"

    def wait_status(self, status, timeout=3.0):
        start_time = time.time()
        while self.get_status(False) != status:
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.01)
        return True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class Stddaq(Array10):
    """
    Retrieves data from Stddaq services, as live streams or replay.
    """
    DEFAULT_URL = os.environ.get("STDDAQ_DEFAULT_URL", "sf-daq-6.psi.ch:6379")

    def __init__(self, url=DEFAULT_URL, name=None, replay=False, **kwargs):
        """
        url (str, optional): URL for Stddaq Redis repo.
        name (str): device name
        replay (str, optional): If True data is retrieved from the buffer (PULL).
                                If False data is live streamed (SUB).
        """
        if redis is None:
            raise Exception("Redis library not available")
        self.host, self.port = get_host_port_from_stream_address(url)
        self.address = url
        self.replay = replay
        self.db = '0'
        mode = "PULL" if replay else "SUB"
        if name:
            url = self.get_instance_stream(name + ":REPLAY-STREAM" if replay else name + ":LIVE-STREAM")
        Array10.__init__(self, url=url, mode=mode, name=name, **kwargs)

    def get_instance_stream(self, name):
        with redis.Redis(host=self.host, port=self.port, db=self.db) as r:
            ret = r.get(name)
            return ret.decode('utf-8').strip() if ret else ret

    def run(self, query):
        control_socket = None
        if self.replay:
            if not self.range.is_by_id():
                raise Exception("Time range not implemented yet")
            if self.range.relative_start or self.range.relative_end:
                raise Exception("Relative range not implemented yet")
            control_socket_uri = "ws://" + self.host + ":8085"
            control_socket = WebSocketClient(control_socket_uri)
            control_socket.start()
            _logger.info ("Status Init: " + control_socket.get_status())
            if control_socket.get_status() != "idle":
                _logger.info("Trying to stop ongoing replay")
                control_socket.send_stop()
                if not control_socket.wait_status("idle", 5):
                    raise Exception("Cannot initialize replay")
                _logger.info("Status Init: " + control_socket.get_status())
            control_socket.send_start(start_id=self.range.start_id, end_id=self.range.end_id)
            _logger.info("Status command: " + control_socket.get_status())
        try:
            Array10.run(self, query=query)
            if control_socket:
                _logger.info("Status completion: " + control_socket.get_status())
                control_socket.send_command({"command": "stop"})
        finally:
            if control_socket:
                _logger.info("Status final: " + control_socket.get_status())
                control_socket.close()


    def search(self, regex=None, case_sensitive=True):
        redis_source = datahub.Redis(url=self.address, backend=self.db)
        return redis_source.search(regex, case_sensitive)

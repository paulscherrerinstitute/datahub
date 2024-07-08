from bsread.sender import Sender, BIND, CONNECT
from bsread import PUB, SUB, PUSH, PULL


def create_sender(port, mode, block=False, queue_size=10, compression=None):
    if mode == "PUB":
        mode = PUB
    if mode == "PUSH":
        mode = PUSH
    sender = Sender(port=port,
                address="tcp://*",
                conn_type=BIND,
                mode=mode,
                queue_size=queue_size,
                block=block,
                data_compression=compression,
                data_header_compression=None)
    sender.open()
    return sender
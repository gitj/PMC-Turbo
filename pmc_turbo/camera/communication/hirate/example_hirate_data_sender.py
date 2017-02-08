from __future__ import division

import IPython
import numpy as np
from pmc_turbo.camera.communication import constants

from pmc_turbo.camera.communication.hirate import hirate_sending_methods

IP = '192.168.1.54'
# IP address of the NPort
PORT = 4002
# Port which the NPort listens to.

zero_msg = '\x00' * 2041
np.random.seed(0)
random_msg = np.random.randint(0, 255, size=10e3).astype('uint8')

incrementing_msg = (np.arange(0, 3000) % 255).astype('uint8')

num_headers = 5
len_data_packet = 2041 - num_headers


def send(msg):
    hirate_sending_methods.send(msg, IP, PORT)


def get_chunks(msg):
    return hirate_sending_methods.chunk_data_by_size(chunk_size=1000, start_byte=constants.SIP_START_BYTE,
                                                     file_id=0, data=msg)


def get_unaltered_chunks(chunk_size, msg):
    return hirate_sending_methods.chunk_data_by_size_no_changes(chunk_size, data=msg)


def send_chunks(chunks):
    for chunk in chunks:
        send(chunk)


def get_packets_from_buffer(buffer):
    START_BYTE = chr(constants.START_BYTE)
    packets = []
    while buffer:
        idx = buffer.find(START_BYTE)
        if idx == -1:
            return packets
        end = buffer[idx + 1:].find(START_BYTE)
        if end == -1:
            packets.append(buffer[idx:])
            return packets
        packets.append(buffer[idx:end])
        buffer = buffer[end:]


def main():
    IPython.embed()


if __name__ == "__main__":
    main()

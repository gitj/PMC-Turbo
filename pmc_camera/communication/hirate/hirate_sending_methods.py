from __future__ import division
import struct
import socket
from pmc_camera.communication import constants
import numpy as np

def send(msg, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (ip, port))
    sock.close()

def chunk_data_by_size(chunk_size, file_id, data):
    chunks = []
    num_chunks = np.ceil(len(data) / chunk_size)
    for i in range(int(num_chunks)):
        msg = data[(i * chunk_size):((i + 1) * chunk_size)]
        format_string = '4B%ds' % len(msg)
        chunk = struct.pack(format_string, constants.SYNC_BYTE, file_id, i, num_chunks, msg)
        # chunk += struct.pack('1B', END_BYTE)
        chunks.append(chunk)
    return chunks
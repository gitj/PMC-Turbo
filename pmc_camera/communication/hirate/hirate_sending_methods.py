from __future__ import division
import struct
import socket
from pmc_camera.communication import constants
from pmc_camera.communication.hirate import cobs_encoding
import numpy as np
import time


def send(msg, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (ip, port))
    sock.close()


def chunk_data_by_size(chunk_size, start_byte, file_id, data):
    chunks = []
    num_chunks = np.ceil(len(data) / chunk_size)
    for i in range(int(num_chunks)):
        msg = data[(i * chunk_size):((i + 1) * chunk_size)]
        format_string = '<4B%ds' % len(msg)
        chunk = struct.pack(format_string, start_byte, file_id, i, num_chunks, msg)
        # chunk += struct.pack('1B', END_BYTE)
        chunks.append(chunk)
    return chunks


def chunk_data_by_size_no_changes(chunk_size, data):
    chunks = []
    num_chunks = np.ceil(len(data) / chunk_size)
    for i in range(int(num_chunks)):
        msg = data[(i * chunk_size):((i + 1) * chunk_size)]
        chunks.append(msg)
    return chunks


def get_buffer_from_file(filename):
    buffer = ''
    with open(filename, 'rb') as f:
        byte = f.read(1)
        buffer += byte
        while byte:
            byte = f.read(1)
            buffer += byte
    return buffer


def ez_send(filename, chunk_size=100, start_byte=constants.HIRATE_START_BYTE, file_id=0, IP='192.168.1.54', PORT=4002):
    zeros = '\x00' * 2041
    send(zeros, IP, PORT)
    time.sleep(0.2)
    data = get_buffer_from_file(filename)
    #data = cobs_encoding.encode_data(data, escape_character=start_byte)
    #chunks = chunk_data_by_size(chunk_size, start_byte, file_id, data)
    chunks = chunk_data_by_size_no_changes(100, data)
    print len(chunks)
    for chunk in chunks:
        send(chunk, ip=IP, port=PORT)
        time.sleep(0.2)
    send(zeros, IP, PORT)

def ez_send_encoding(filename, chunk_size=100, start_byte=constants.TEST_START_BYTE, file_id=0, IP='192.168.1.54', PORT=4002):
    zeros = '\x00' * 2041
    send(zeros, IP, PORT)
    time.sleep(0.2)
    data = get_buffer_from_file(filename)
    data = cobs_encoding.encode_data(data, escape_character=start_byte)
    chunks = chunk_data_by_size(chunk_size, start_byte, file_id, data)
    print len(chunks)
    for chunk in chunks:
        send(chunk, ip=IP, port=PORT)
        time.sleep(0.2)
    send(zeros, IP, PORT)

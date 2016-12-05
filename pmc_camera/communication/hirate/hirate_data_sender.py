from __future__ import division
import socket
import struct
import numpy as np
import IPython

import cobs_encoding

IP = '192.168.1.253'
# IP address of the NPort
PORT = 4002
# Port which the NPort listens to.

msg = '\x00' * 2041
np.random.seed(0)
random_msg = np.random.randint(0, 255, size=10e3).astype('uint8')

num_headers = 5
len_data_packet = 2041 - num_headers


def send(msg):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (IP, PORT))
    sock.close()


def chunk_data(data, file_id):
    packets = []
    num_packets = np.ceil(len(data) / len_data_packet)
    for i in range(int(num_packets)):
        msg = data[(i * len_data_packet):((i + 1) * len_data_packet)]
        format_string = '%dB%dB' % (num_headers, len(msg))
        packet = struct.pack(format_string, 99, 0, i, num_packets, file_id, *msg)
        if len(msg) < len_data_packet:
            padding = '\x00' * (len_data_packet - len(msg))
            packet += padding
        #packet = cobs_encoding.encode_data(packet)
        packets.append(packet)
    return packets


def create_shuffled_data():
    packets = chunk_data(random_msg, 32)
    shuffled_packets = [packets[4], packets[0], packets[1], packets[2], packets[3]]
    return shuffled_packets


def create_and_send_two_files():
    packets1 = chunk_data(random_msg, 32)
    packets2 = chunk_data(random_msg, 23)
    for i in range(len(packets1)):
        send(packets1[i])
        send(packets2[i])


def main():
    IPython.embed()


if __name__ == "__main__":
    main()

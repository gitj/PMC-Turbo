from __future__ import division
import time
import serial
import socket
import IPython
import numpy as np
import gse_receiver
from pmc_camera.communication import downlink_classes

DOWNLINK_IP, DOWNLINK_PORT = '192.168.1.54', 4002
np.random.seed(0)


# DATA = np.random.randint(0, 255, size=10000).astype('uint8')

def send(msg, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = sock.sendto(msg, (ip, port))
    sock.close()


def send_and_receive_loop(data, chunk_size, downlink_bytes_per_sec):
    received_buffer = ''
    ser = serial.Serial(port='/dev/ttyUSB0', baudrate=115200)
    ser.timeout = 0
    time_per_chunk = chunk_size / downlink_bytes_per_sec
    last_sent_at = 0
    start_time = time.time()
    last_update = 0
    data_to_send = data
    while data_to_send:
        if time.time() - last_sent_at > time_per_chunk:
            send(data_to_send[:chunk_size], DOWNLINK_IP, DOWNLINK_PORT)
            data_to_send = data_to_send[chunk_size:]
            last_sent_at = time.time()
        received_buffer += ser.readall()
        if time.time() - last_update > 10:
            print 'Bytes sent: %d' % (len(data) - len(data_to_send))
            print 'Actual byte rate %f' % (len(received_buffer) / (time.time() - start_time))
            print 'Bytes receuvedl %d' % (len(received_buffer))
    ser.close()
    return received_buffer


def main(data_length, chunk_size, downlink_bytes_per_sec):
    DATA = np.arange(0, data_length, dtype='>u2').view('uint8')
    DATA[DATA == 0xFA] = 0x55
    DATA = DATA.tostring()
    gr = gse_receiver.GSEReceiver()
    buffer = send_and_receive_loop(DATA, chunk_size, downlink_bytes_per_sec)
    gse_packets, _ = gr.get_gse_packets_from_buffer(buffer)
    hi, low = gr.separate_hirate_and_lowrate_gse_packets(gse_packets)
    data_buffer = ''
    for p in hi:
        data_buffer += p.payload
    return data_buffer
    # array = np.fromstring(data_buffer[1:-1], dtype='>u2')
    # return array


"""
def send_and_receive_data_as_packets():
    dl = downlink_classes.HirateDownlink(downlink_ip=DOWNLINK_IP, downlink_port=DOWNLINK_PORT,
                                         downlink_speed=DOWNLINK_SPEED)

    dl.put_data_into_queue(DATA, file_id=1, file_type=1, packet_size=1000)
    print len(dl.packets_to_send)
    buffer = ''
    start = time.time()
    while (time.time() - start) < 60:
        if dl.packets_to_send:
            dl.send_data()
        buffer += get_new_data_into_buffer(1)
    return buffer


def get_packets(buffer):
    gr = gse_receiver.GSEReceiver()
    gse_packets, _ = gr.get_gse_packets_from_buffer(buffer)
    # hirate_packets, lowrate_packets = gr.separate_hirate_and_lowrate_gse_packets(gse_packets)
    return gse_packets


def find_indices(hirate_packets):
    zero_packet_index = 0
    for i, packet in enumerate(hirate_packets):
        if packet.packet_number == 0:
            zero_packet_index = i
            break

    data_packets = hirate_packets[zero_packet_index:]
    data_buffer = ''
    for packet in data_packets:
        data_buffer += packet.payload
    indices = []
    for idx, byte in enumerate(data_buffer):
        if byte != DATA[idx]:
            indices.append(idx)
    return indices


def get_new_data_into_buffer(time_loop, usb_port_address='/dev/ttyUSB0', baudrate=115200):
    buffer = ''
    ser = serial.Serial(usb_port_address, baudrate=baudrate)
    ser.timeout = 1
    start = time.time()
    while (time.time() - start) < time_loop:
        data = ser.read(10000)
        buffer += data
    ser.close()
    return buffer
"""

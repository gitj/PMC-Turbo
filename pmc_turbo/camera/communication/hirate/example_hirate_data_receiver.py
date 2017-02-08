import struct

import IPython
import numpy as np
import serial
from pmc_turbo.camera.communication.hirate import hirate_receiving_methods

import cobs_encoding
import example_hirate_data_sender

USB_PORT_ADDRESS = '/dev/ttyUSB0'
BAUDRATE = 9600
num_headers = 5
len_data_packet = 2041 - num_headers

np.random.seed(0)
random_msg = np.random.randint(0, 255, size=10e3).astype('uint8')


def create_fake_packets():
    data = cobs_encoding.encode_data(random_msg)
    return example_hirate_data_sender.get_chunks(data)


def create_fake_buffer():
    buffer = ''
    packets = create_fake_packets()
    for packet in packets:
        buffer += packet
    return buffer


def run_raw_loop():
    ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)
    ser.timeout = 1
    while True:
        data = ser.read(2041)

        format_string = '%dB' % len(data)
        d = struct.unpack(format_string, data)
        print d
    ser.close()


def get_data(loop_time=30):
    return hirate_receiving_methods.gather_data_and_put_into_buffer(USB_PORT_ADDRESS, BAUDRATE, loop_time)


def get_packets(buffer):
    return hirate_receiving_methods.get_packets_from_buffer(buffer)


def get_files(packets):
    return hirate_receiving_methods.packets_to_files(packets)


def test_equality(msg):
    msg = struct.unpack(('%dB' % len(msg)), msg)
    return np.equal(np.array(msg).astype('uint8')[:10000], random_msg)


def main():
    IPython.embed()


if __name__ == "__main__":
    main()

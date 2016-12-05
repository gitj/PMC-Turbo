import serial
import struct
import operator
import IPython
import numpy as np
import cobs_encoding

USB_PORT_ADDRESS = '/dev/ttyUSB0'
BAUDRATE = 9600
num_headers = 5
len_data_packet = 2041 - num_headers

np.random.seed(0)
random_msg = np.random.randint(0, 255, size=10e3).astype('uint8')


def run_raw_loop():
    ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)
    ser.timeout = 1
    while True:
        data = ser.read(2041)

        format_string = '%dB' % len(data)
        d = struct.unpack(format_string, data)
        print d
    ser.close()


def gather_packets_and_assemble():
    ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)
    ser.timeout = 1
    files_received = {}
    indices_received = []
    while True:
        data = ser.read(2041)
        if data:
            print 'Data received.'
            format_string = '5B%ds' % (len(data)-5)
            start, type, n, m, file_id, msg = struct.unpack(format_string, data)
            print start, type, n, m, file_id
            #msg = cobs_encoding.decode_data(msg)
            packet = {'start': start, 'type': type, 'n': n, 'm': m, 'file_id': file_id, 'data': msg}
            if packet['file_id'] in files_received:
                files_received[packet['file_id']]['packets_received'].append(packet)
                files_received[packet['file_id']]['indices_received'].append(n)
                print [i in files_received[packet['file_id']]['indices_received'] for i in range(m)]
                if False not in [i in files_received[packet['file_id']]['indices_received'] for i in range(m)]:
                    return assemble_packets(files_received[packet['file_id']]['packets_received'])
            else:
                files_received[packet['file_id']] = {}
                files_received[packet['file_id']]['packets_received'] = [packet]
                files_received[packet['file_id']]['indices_received'] = [n]
    ser.close()


def test_equality(msg):
    msg = struct.unpack(('%dB' % len(msg)), msg)
    return np.equal(np.array(msg).astype('uint8')[:10000], random_msg)


def assemble_packets(packets):
    sorted_packets = sorted(packets, key=lambda k: k['n'])
    accumulated_data = ''
    for packet in sorted_packets:
        print packet['n']
        accumulated_data += packet['data']

    return accumulated_data


def main():
    IPython.embed()


if __name__ == "__main__":
    main()

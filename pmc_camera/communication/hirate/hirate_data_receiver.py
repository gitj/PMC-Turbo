from cookielib import reach

import serial
import struct
import operator
import IPython
import numpy as np
import cobs_encoding
import time
import hirate_data_sender

USB_PORT_ADDRESS = '/dev/ttyUSB0'
BAUDRATE = 9600
num_headers = 5
len_data_packet = 2041 - num_headers

np.random.seed(0)
random_msg = np.random.randint(0, 255, size=10e3).astype('uint8')


def create_fake_packets():
    data = cobs_encoding.encode_data(random_msg)
    return hirate_data_sender.chunk_data_by_size(1000, 0, data=data)


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


def gather_data_and_put_into_buffer(loop_time):
    ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)
    ser.timeout = 1
    buffer = ''
    start = time.time()
    while time.time() - start < loop_time:
        data = ser.read(2041)
        buffer += data
    ser.close()
    return buffer


def get_packets_from_buffer(buffer):
    START_BYTE = '\x10'
    packets = []
    while buffer:
        idx = buffer.find(START_BYTE)
        if idx == -1:
            return packets
        next_idx = buffer[idx + 1:].find(START_BYTE)
        # This is necessary since we ignore the first idx.
        if next_idx == -1:
            packets.append(buffer[idx:])
            return packets
        packets.append(buffer[idx:next_idx + 1])
        buffer = buffer[next_idx + 1:]


def packets_to_files(packets):
    files = {}
    reassembled_files = {}
    for packet in packets:
        print '%r' % packet[:4]
        print len(packet[4:])
        start, file_id, n, num_chunks = struct.unpack('4B', packet[:4])
        packet_dict = {'n': n, 'num_chunks': num_chunks, 'data': packet[4:]}
        if file_id in files.keys():
            files[file_id].append(packet_dict)
        else:
            files[file_id] = [packet_dict]

    for key in files:
        packet_dicts = files[key]
        num_chunks = packet_dicts[0]['num_chunks']
        if False not in [packet['num_chunks'] == num_chunks for packet in packet_dicts]:
            # Check that they all agree on the number of chunks
            packet_nums = [packet['n'] for packet in packet_dicts]
            if False not in [i in packet_nums for i in range(num_chunks)]:
                sorted_packets = sorted(packet_dicts, key=lambda k: k['n'])
                # sorted_packets = sorted(packets.items(), key=operator.itemgetter('n'))
                accumulated_data = ''
                for packet in sorted_packets:
                    accumulated_data += packet['data']
                reassembled_files[key] = accumulated_data
    return reassembled_files


def test_equality(msg):
    msg = struct.unpack(('%dB' % len(msg)), msg)
    return np.equal(np.array(msg).astype('uint8')[:10000], random_msg)


'''
Old methods
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





def assemble_packets(packets):
    sorted_packets = sorted(packets, key=lambda k: k['n'])
    accumulated_data = ''
    for packet in sorted_packets:
        print packet['n']
        accumulated_data += packet['data']

    return accumulated_data
    '''


def main():
    IPython.embed()


if __name__ == "__main__":
    main()

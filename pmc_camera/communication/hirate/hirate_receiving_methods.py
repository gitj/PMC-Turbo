import serial
import struct
import time

def gather_data_and_put_into_buffer(usb_port_address, baudrate, loop_time):
    ser = serial.Serial(usb_port_address, baudrate=baudrate)
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
        #print '%r' % packet[:4]
        #print len(packet[4:])
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
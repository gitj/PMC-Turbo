import os
import struct
import time

import serial
from pmc_turbo.camera.communication import constants

import cobs_encoding
from pmc_turbo.camera.communication import packet_classes


def gather_data_and_write_to_disk(usb_port_address='/dev/ttyUSB0', baudrate=115200, path='./received_sip_data'):
    ser = serial.Serial(usb_port_address, baudrate=baudrate)
    ser.timeout = 1
    filename = os.path.join(path, time.strftime('%Y-%m-%d_%H%M%S.txt'))
    while True:
        data = ser.read(10000)
        print '%r' % data
        if data:
            f = open(filename, 'ab+')
            f.write(data)
            f.close()
    ser.close()


def get_sip_packets_from_buffer(buffer):
    leftover, ps = find_sip_packets_in_buffer(buffer)
    packets = []
    for p in ps:
        packet = packet_classes.SIPPacket()
        packet.from_buffer(p)
        packets.append(packet)
    return packets


def get_hirate_packets_from_sip_packets(sip_packets, start_byte):
    sip_data = ''
    for packet in sip_packets:
        sip_data += packet.data
    return get_hirate_packets_from_buffer(sip_data, start_byte)


def get_sip_packets_from_file(filename):
    f = open(filename, 'rb')
    buffer = f.read()
    f.close()
    return get_sip_packets_from_buffer(buffer)


def get_hirate_packets_from_buffer(buffer, start_byte):
    # Later, this should also return
    packets = []
    while buffer:
        idx = buffer.find(start_byte)
        if idx == -1:
            print '1'
            return packets
        if len(buffer) < idx + 8:
            print '2'
            return packets
        length, = struct.unpack('>1H', buffer[idx + 4:idx + 6])
        if len(buffer) < idx + 6 + length + 2:
            print '3'
            return packets
        packet = packet_classes.FilePacket()
        packet.from_buffer(buffer[idx:idx + 6 + length + 2])
        packets.append(packet)
        buffer = buffer[idx + 6 + length + 2:]


def example():
    # '2016-12-14_183618.txt' was sent from hirate sending methods ez_send_using_packets. See that function for details.
    sip_packets = get_sip_packets_from_file('./received_sip_data/2016-12-14_183618.txt')
    hirate_packets = get_hirate_packets_from_sip_packets(sip_packets, '\x17')
    data_packets = [packet for packet in hirate_packets if packet.file_id == 1]
    jpg_buffer = ''
    for packet in data_packets:
        jpg_buffer += packet.data
    decoded_jpg_buffer = cobs_encoding.decode_data(jpg_buffer, escape_character=0x17)
    with open('mytest.jpg', 'wb') as f:
        f.write(decoded_jpg_buffer)


def get_stuff_from_filename(filename, file_id, escape_character):
    sip_packets = get_sip_packets_from_file(filename)
    hirate_packets = get_hirate_packets_from_sip_packets(sip_packets, '\x17')
    data_packets = [packet for packet in hirate_packets if packet.file_id == file_id]
    jpg_buffer = ''
    for packet in data_packets:
        jpg_buffer += packet.data
    #decoded_jpg_buffer = cobs_encoding.decode_data(jpg_buffer, escape_character=ord(escape_character))
    return sip_packets, hirate_packets, data_packets, jpg_buffer#, decoded_jpg_buffer
    # with open('mytest.jpg', 'wb') as f:
    #    f.write(decoded_jpg_buffer)


def write_buffer_to_file(filename, buffer):
    with open(filename, 'wb') as f:
        f.write(buffer)


def get_jpeg_from_filename(filename, file_id, escape_character):
    _, _, _, _, decoded_buffer = get_stuff_from_filename(filename, file_id, escape_character)
    write_buffer_to_file('tmp.jpg', decoded_buffer)


##############################################################


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


def get_packets_from_buffer(buffer, start_byte):
    packets = []
    while buffer:
        idx = buffer.find(start_byte)
        if idx == -1:
            return packets
        next_idx = buffer[idx + 1:].find(start_byte)
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
        # print '%r' % packet[:4]
        # print len(packet[4:])
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


def find_sip_packets_in_buffer(buffer):
    leftover_buffer = ''
    sip_packets = []
    while buffer:
        idx = buffer.find(chr(constants.SYNC_BYTE))
        if idx == -1:
            leftover_buffer += buffer
            buffer = ''
            continue

        if not len(buffer) > (idx + 6):
            # Buffer doesn't have minimum length to include length bytes, thus packets
            leftover_buffer += buffer
            buffer = ''
            continue

        if not ord(buffer[idx + 1]) in [0xfa, 0xfb, 0xfc, 0xfd, 0xff]:
            leftover_buffer += buffer[:idx + 1]
            buffer = buffer[idx + 1:]
            continue
        if ord(buffer[idx + 2]) & 0xf0:
            leftover_buffer += buffer[:idx + 1]
            buffer = buffer[idx + 1:]
            continue
        length, = struct.unpack('>1H', buffer[idx + 4:idx + 6])
        # These two bytes are the length. Most significant byte first, unlike most of the SIP communication protocols.
        if not len(buffer) > (idx + 5 + length + 1):
            # Buffer doesn't have minimum length to include checksum byte, and thus packet
            leftover_buffer += buffer
            buffer = ''
            continue
        checksum_byte = ord(buffer[idx + 5 + length + 1])
        sum = 0
        for byte in buffer[idx + 2:idx + 5 + length + 1]:
            sum += ord(byte)
        sum %= 256
        # Sum needs to be mode 256 to fit in 1 byte.
        if sum != checksum_byte:
            leftover_buffer += buffer[:idx + 1]
            buffer = buffer[idx + 1:]
            continue
        # Need to verify checksum here.
        if sum == checksum_byte:
            sip_packets.append(buffer[idx:(idx + 5 + length + 1) + 1])
            leftover_buffer += buffer[:idx]
            buffer = buffer[(idx + 5 + length + 1) + 1:]
            continue

    return leftover_buffer, sip_packets

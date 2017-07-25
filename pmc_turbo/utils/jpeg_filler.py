from pmc_turbo.communication import packet_classes, file_format_classes
import numpy as np


def construct_jpeg(packets):
    sorted_packets = sorted(packets, key=lambda k: k.packet_number)
    packet_length = sorted_packets[0].payload_length
    data_buffer = ''
    i = 0
    while i < len(sorted_packets):
        packet_number = sorted_packets[i].packet_number
        if packet_number == i:
            data_buffer += sorted_packets[i].payload
            i += 1
        if packet_number > i:
            data_buffer += np.zeros(packet_length, dtype=np.uint8)
            i += 1
        else:
            data_buffer += np.zeros((packet_length - i), dtype=np.uint8)
            i = packet_number
    return data_buffer


def assemble_file_from_packets(self, packets):
    data_buffer = ''.join([packet.payload for packet in packets])
    return file_format_classes.decode_file_from_buffer(data_buffer)


def put_data_into_packets(buffer, file_id, packet_size=1000):
    packets = []
    num_packets = int(np.ceil(len(buffer) / packet_size))
    for i in range(num_packets):
        msg = buffer[(i * packet_size):((i + 1) * packet_size)]
        packet = packet_classes.FilePacket(file_id=file_id, packet_number=i,
                                           total_packet_number=num_packets, payload=msg)
        packets.append(packet)
    return packets


def _get_data_for_tests():
    with open('2017-07-25_174523_002255.jpg', 'rb') as f:
        buffer = f.read()
    return buffer

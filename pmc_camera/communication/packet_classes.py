import struct
import numpy as np
from PyCRC.CRCCCITT import CRCCCITT


def get_checksum(data):
    return np.sum(np.frombuffer(data, dtype='uint8'), dtype='uint8')


def get_crc(data):
    return CRCCCITT().calculate(data)


class SIPPacket():
    def __init__(self):
        self.header_format_string = '>4B1H'
        self.header_length = 6
        return

    def from_buffer(self, buffer):
        self.start_byte, self.sync2, self.origin, _, self.length = struct.unpack(self.header_format_string,
                                                                                 buffer[:self.header_length])
        self.data = buffer[self.header_length:-1]
        self.checksum = ord(buffer[-1])

    def to_buffer(self):
        header_buff = struct.pack(self.header_format_string, self.start_byte, self.sync2, self.origin, 0, self.length)
        return header_buff + self.data + chr(get_checksum(self.data))


class HiratePacket():
    def __init__(self):
        self.header_format_string = '>4B1H'
        self.header_length = 6

    def from_arguments(self, start_byte, file_id, packet_number, total_packet_number, data):
        self.start_byte = start_byte
        self.file_id = file_id
        self.packet_number = packet_number
        self.total_packet_number = total_packet_number
        self.data = data
        self.length = len(data)
        self.crc = get_crc(data)

    def from_buffer(self, buffer):
        self.start_byte, self.file_id, self.packet_number, self.total_packet_number, self.length = struct.unpack(
            self.header_format_string,
            buffer[:self.header_length])
        self.data = buffer[self.header_length:-2]
        if len(self.data) != self.length:
            raise AttributeError('Data length and predicted data length do not match.')
        self.crc, = struct.unpack('>1H', buffer[-2:])

    def to_buffer(self):
        header_buff = struct.pack(self.header_format_string, self.start_byte, self.file_id, self.packet_number,
                                  self.total_packet_number, self.length)
        crc_buff = struct.pack('>1H', self.crc)
        return header_buff + self.data + crc_buff

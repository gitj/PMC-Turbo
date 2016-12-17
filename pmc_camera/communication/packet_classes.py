import struct
import numpy as np
from PyCRC.CRCCCITT import CRCCCITT

def get_checksum(data):
    return int(np.sum(np.frombuffer(data, dtype='uint8'), dtype='uint8'))


def get_crc(data):
    return CRCCCITT().calculate(data)

class PacketError(RuntimeError):
    """
    General packet exception
    """
    pass

class PacketLengthError(PacketError):
    """
    Exception for packets that are shorter or longer than their length field specifies
    """
    pass

class PacketChecksumError(PacketError):
    """
    Exception for packets that don't pass checksum or CRC tests
    """
    pass

class GSEPacket(object):
    _header_format_string = '>4B1H'
    _valid_start_byte = 0xFA
    _valid_sync2_bytes = [0xFA, 0xFB, 0xFC, 0xFD, 0xFF]
    def __init__(self,buffer=None,sync2_byte=None,origin=None,payload=None,greedy=True):
        """
        GSE style packet, received from the GSE and passed to the ground computer.

        This could contain either low rate or high rate data.

        To decode a packet, use as GSEPacket(data), and access the payload attribute. This will raise a PacketError or
        subclass if something serious is wrong, and set the is_valid attribute False if the sync2_byte is not
        recognized.

        To construct a packet, use as
        packet = GSEPacket(sync2_byte=0xFA,origin=1,payload="hello world")
        data = packet.to_buffer()

        Parameters
        ----------
        buffer : string
            A data buffer to decode as a packet
        sync2_byte :
            sync2 byte indicates the communications link. see SIP manual
        origin : uint8
            origin byte, see SIP manual
        payload : string
            Bytes to package into the packet
        greedy : bool
            Only used for decoding.
            If true, assume the buffer contains exactly one packet.
            If false, use the length field of the packet to decide how much of the buffer to interpret.
        """
        self._header_length = struct.calcsize(self._header_format_string)
        self._minimum_buffer_length = self._header_length + 1
        self.is_valid = False
        if buffer is not None:
            self.from_buffer(buffer, greedy=greedy)
        else:
            self.sync2_byte = sync2_byte
            self.origin = origin
            self.payload = payload
            self.payload_length = len(payload)
            self.payload_checksum = get_checksum(payload)
            self.start_byte = self._valid_start_byte

    def from_buffer(self,buffer, greedy=True):
        """
        Decode and validate the given buffer and update the class attributes accordingly

        Parameters
        ----------
        buffer : str
            buffer to decode as a packet
        greedy : bool
            If true, assume the buffer contains exactly one packet.
            If false, use the length field of the packet to decide how much of the buffer to interpret.
        """
        if len(buffer) < self._minimum_buffer_length:
            raise PacketLengthError("Buffer of length %d is too short to contain a packet (minimum length is %d)" %
                                       (len(buffer),self._minimum_buffer_length))
        self.start_byte, self.sync2_byte, self.origin, _, self.payload_length = struct.unpack(
            self._header_format_string, buffer[:self._header_length])
        if greedy:
            checksum_index = -1
        else:
            checksum_index = self._header_length+self.payload_length+1
        payload = buffer[self._header_length:checksum_index]
        if len(payload) != self.length:
            raise PacketLengthError("Payload length %d does not match length field value %d" %(len(payload),
                                                                                                self.length))

        payload_checksum = get_checksum(payload)
        if payload_checksum != ord(buffer[checksum_index]):
            raise PacketChecksumError("Payload checksum %d does not match checksum field value %d" %
                                      (payload_checksum,ord(buffer[checksum_index])))
        self.payload = payload
        self.payload_checksum = payload_checksum
        if self.sync2_byte not in self._valid_sync2_bytes:
            self.is_valid = False
        else:
            self.is_valid = True

    def to_buffer(self):
        """
        Construct the packet string

        Returns
        -------
        buffer : string containing the packet
        """
        assert (self.sync2_byte is not None) and (self.origin is not None) and (self.payload is not None)
        header = struct.pack(self._header_format_string, self.start_byte, self.sync2_byte, self.origin, 0,
                             self.payload_length)
        return header + self.payload + chr(self.payload_checksum)

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

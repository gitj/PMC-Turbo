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

    def __init__(self, buffer=None, sync2_byte=None, origin=None, payload=None, greedy=True):
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

    def _repr_(self):
        return 'Sync2: %d \n Origin: %d \n Payload Length %d \n First 10 bytes: %s' % (self.sync2_byte,
                                                                                       self.origin, self.payload_length,
                                                                                       self.payload[:10])

    def from_buffer(self, buffer, greedy=True):
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
                                    (len(buffer), self._minimum_buffer_length))
        self.start_byte, self.sync2_byte, self.origin, _, self.payload_length = struct.unpack(
            self._header_format_string, buffer[:self._header_length])
        if greedy:
            checksum_index = -1
        else:
            checksum_index = self._header_length + self.payload_length + 1
        payload = buffer[self._header_length:checksum_index]
        if len(payload) != self.length:
            raise PacketLengthError("Payload length %d does not match length field value %d" % (len(payload),
                                                                                                self.length))

        payload_checksum = get_checksum(payload)
        if payload_checksum != ord(buffer[checksum_index]):
            raise PacketChecksumError("Payload checksum %d does not match checksum field value %d" %
                                      (payload_checksum, ord(buffer[checksum_index])))
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


class HiratePacket(object):
    _header_format_string = '>4B1H'
    _valid_start_byte = 0x17

    def __init__(self, buffer=None, file_id=None, packet_number=None, total_packet_number=None, payload=None,
                 greedy=True):
        """
        Hirate packet. We break data into chunks and send them to the SIP in this packet format.

        To decode a packet, use as HiratePacket(data), and access the payload attribute.

        To construct a packet, use as
        packet = GSEPacket(file_id=101,packet_number=2,total_packet_number=4,payload="hello world")
        data = packet.to_buffer()

        Parameters
        ----------
        buffer : string
            A data buffer to decode as a packet
        file_id : uint8
            file_id assigned to file when breaking it up to send.
        packet_number : uint8
            Nth packet in file with file_id
        total_packet_number : uint8
            Total number of packets in file
        payload : string
            Bytes to package into the packet
        greedy : bool
            Only used for decoding.
            If true, assume the buffer contains exactly one packet.
            If false, use the length field of the packet to decide how much of the buffer to interpret.
        """
        self._header_length = struct.calcsize(self._header_format_string)
        self._minimum_buffer_length = self._header_length + 1
        if buffer is not None:
            self.from_buffer(buffer, greedy=greedy)
        else:
            self.file_id = file_id
            self.packet_number = packet_number
            self.total_packet_number = total_packet_number
            self.payload = payload
            self.payload_length = len(payload)
            self.payload_crc = get_crc(payload)
            self.start_byte = self._valid_start_byte

    def _repr_(self):
        return 'File_id: %d \n Packet Number %d of %d \n First 10 bytes: %s' % (
            self.file_id, self.packet_number, self.total_packet_number, self.payload[:10])

    def from_buffer(self, buffer, greedy=True):
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
                                    (len(buffer), self._minimum_buffer_length))
        self.start_byte, self.file_id, self.packet_number, self.total_packet_number, self.payload_length = struct.unpack(
            self._header_format_string, buffer[:self._header_length])
        if greedy:
            crc_index = -1
        else:
            crc_index = self._header_length + self.payload_length + 1
        payload = buffer[self._header_length:checksum_index]
        if len(payload) != self.length:
            raise PacketLengthError("Payload length %d does not match length field value %d" % (len(payload),
                                                                                                self.length))

        payload_crc = get_crc(payload)
        if payload_crc != ord(buffer[crc_index]):
            raise PacketChecksumError("Payload CRC %d does not match CRC field value %d" %
                                      (payload_crc, ord(buffer[crc_index])))
        self.payload = payload
        self.payload_crc = payload_crc

    def to_buffer(self):
        """
        Construct the packet string

        Returns
        -------
        buffer : string containing the packet
        """
        assert (self.file_id is not None) and (self.packet_number is not None) and (
            self.total_packet_number is not None) and (self.payload is not None)
        header = struct.pack(self._header_format_string, self.start_byte, self.file_id, self.packet_number,
                             self.total_packet_number,
                             self.payload_length)
        return header + self.payload + chr(self.payload_crc)

import struct
import numpy as np
from PyCRC.CRCCCITT import CRCCCITT
import logging

logger = logging.getLogger(__name__)


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


class PacketValidityError(PacketError):
    """
    Exception for packets which are clearly not valid
    """
    pass


class GSEPacket(object):
    _metadata_table = [('1B', 'start_byte'),
                       ('1B', 'sync2_byte'),
                       ('1B', 'origin_byte'),
                       ('1B', 'unused_zero'),
                       ('1H', 'payload_length')]
    _header_format_string = '>' + ''.join([format for format, name in _metadata_table])
    _valid_start_byte = 0xFA
    _valid_sync2_bytes = [0xFA, 0xFB, 0xFC, 0xFD, 0xFF]
    header_length = struct.calcsize(_header_format_string)

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
        self._minimum_buffer_length = self.header_length + 1
        self.is_valid = False
        if buffer is not None:
            self.from_buffer(buffer, greedy=greedy)
        else:
            self.sync2_byte = sync2_byte
            self.origin = origin
            self.payload = payload
            self.payload_length = len(payload)
            self.checksum = (get_checksum(payload) + self.origin + self.payload_length) % 256
            # This could be clearer, but I don't want to convert origin and payload_length to string.
            self.start_byte = self._valid_start_byte

    def __repr__(self):
        return 'Sync2: 0x%02x \n Origin: %d \n Payload Length %d \n First 10 bytes: %r' % (self.sync2_byte,
                                                                                           self.origin,
                                                                                           self.payload_length,
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
            self._header_format_string, buffer[:self.header_length])
        if greedy:
            checksum_index = -1
        else:
            checksum_index = self.header_length + self.payload_length
        payload = buffer[self.header_length:checksum_index]
        if len(payload) != self.payload_length:
            raise PacketLengthError("Payload length %d does not match length field value %d" % (len(payload),
                                                                                                self.payload_length))

        checksum = get_checksum(buffer[2:checksum_index])
        if checksum != ord(buffer[checksum_index]):
            raise PacketChecksumError("Payload checksum %d does not match checksum field value %d" %
                                      (checksum, ord(buffer[checksum_index])))
        self.payload = payload
        self.checksum = checksum
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
        return header + self.payload + chr(self.checksum)


class HiratePacket(object):
    _metadata_table = [('1B', 'start_byte'),
                       ('1L', 'file_id'),
                       ('1B', 'packet_number'),
                       ('1B', 'total_packet_number'),
                       ('1H', 'payload_length')]
    _header_format_string = '>' + ''.join([format for format, name in _metadata_table])
    _valid_start_byte = 0xFA
    header_length = struct.calcsize(_header_format_string)
    _max_payload_size = 1500

    def __init__(self, buffer=None, file_id=None,
                 packet_number=None, total_packet_number=None, payload=None):
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

        self._minimum_buffer_length = self.header_length + 2
        if buffer is not None:
            self.from_buffer(buffer)
        else:
            self.file_id = file_id
            self.packet_number = packet_number
            self.total_packet_number = total_packet_number
            self.payload = payload
            self.payload_length = len(payload)
            self.payload_crc = get_crc(payload)
            self.start_byte = self._valid_start_byte
        logger.debug('Hirate packet created.')

    def __repr__(self):
        payload = None
        try:
            payload = self.payload[:10]
        except Exception:
            pass
        return 'File_id: %r \n Packet Number %r of %r \n First 10 bytes: %r' % (
            self.file_id, self.packet_number, self.total_packet_number, payload)

    def from_buffer(self, buffer):
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
            self._header_format_string, buffer[:self.header_length])

        if self.payload_length > self._max_payload_size:
            raise PacketValidityError("Payload length is clearly wrong.")

        crc_index = self.header_length + self.payload_length
        payload = buffer[self.header_length:crc_index]

        if len(payload) != self.payload_length:
            raise PacketLengthError("Payload length %d does not match length field value %d" % (len(payload),
                                                                                                self.payload_length))

        payload_crc = get_crc(payload)
        crc_bytes = buffer[crc_index:crc_index + 2]
        if len(crc_bytes) < 2:
            raise PacketLengthError("Buffer length insufficient to contain complete CRC.")
        buffer_crc, = struct.unpack('>1H', crc_bytes)
        if payload_crc != buffer_crc:
            raise PacketChecksumError("Payload CRC %d does not match CRC field value %d \n Packet: %r" %
                                      (payload_crc, buffer_crc, self))
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
        header = struct.pack(self._header_format_string, self.start_byte, self.file_id,
                             self.packet_number, self.total_packet_number, self.payload_length)
        return header + self.payload + struct.pack('>1H', self.payload_crc)

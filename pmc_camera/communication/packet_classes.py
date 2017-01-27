import struct
from multiprocessing import Value

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
            if (sync2_byte is None) or (origin is None) or (payload is None):
                raise ValueError('All parameters must be specified'
                                 '\n Sync2_byte was %r, Origin was %r, Payload was %r' % (sync2_byte, origin, payload))
            if sync2_byte not in self._valid_sync2_bytes:
                raise ValueError('sync2_byte not in valid_sync2_bytes \n Sync2 byte is %r' % sync2_byte)
            if origin >= 16:
                raise ValueError('origin not valid \n Origin is %r' % origin)
            self.sync2_byte = sync2_byte
            self.origin = origin
            self.payload = payload
            self.payload_length = len(payload)
            origin_payload_length_string = struct.pack('>1B1H', self.origin, self.payload_length)
            # Checksum includes origin and payload length; need to put these into the the byte string for calculation.
            self.checksum = get_checksum(payload + origin_payload_length_string)
            self.start_byte = self._valid_start_byte

    def __repr__(self):
        try:
            return 'Sync2: 0x%02x \n Origin: %d \n Payload Length %d \n First 10 bytes: %r' % (self.sync2_byte,
                                                                                               self.origin,
                                                                                               self.payload_length,
                                                                                               self.payload[:10])
        except Exception:
            return '[Invalid Packet]'

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
        if self.start_byte != self._valid_start_byte:
            raise PacketValidityError("First byte is not valid start byte. First byte is %r" % buffer[0])
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
            raise PacketValidityError('Sync2_byte not in valid_sync2_bytes. Sync2 byte is %r' % self.sync2_byte)

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
            if self.packet_number >= self.total_packet_number:
                raise ValueError('Packet number is greater or equal to total packet number.\n'
                                 'Packet number is %r. Total packet number is %r'
                                 % (self.packet_number, self.total_packet_number))
            self.payload = payload
            self.payload_length = len(payload)
            if self.payload_length > self._max_payload_size:
                raise ValueError('Payload length is greater than max_payload_size. \n Length is %r'
                                 % self.payload_length)
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

class CommandPacket(object):
    _header_format_table = [('1B','start_byte'),
                            ('1B','identifier'),
                            ('1B','length'),
                            ]
    _header_format_string = '>' + ''.join([format_ for format_, _ in _header_format_table])
    header_length = struct.calcsize(_header_format_string)
    
    _subheader_format_table = [('1H', 'sequence_number'),
                           ('1B', 'destination')]
    _subheader_format_string = '>' + ''.join([format_ for format_, _ in _subheader_format_table])
    subheader_length = struct.calcsize(_subheader_format_string)
    _footer_format_table = [('1H', 'crc'),
                            ('1B', 'end_byte')]
    _crc_length = 2
    _footer_format_string = '>' + ''.join([format_ for format_, _ in _footer_format_table])
    footer_length = struct.calcsize(_footer_format_string)
    _valid_start_byte = 0x10   # LDB 3.1.2.1
    _valid_end_byte = 0x03
    _valid_identifier = 0x14  # LDB 3.1.3.6
    def __init__(self,buffer=None,payload=None,sequence_number=None,destination=None):
        self._minimum_buffer_length = self.header_length + self.subheader_length + self.footer_length
        if buffer is not None:
            if len(buffer) < self._minimum_buffer_length:
                raise PacketLengthError("Cannot decode %r as CommandPacket because length %d is less than minimum %d"
                                 % (buffer,len(buffer),self._minimum_buffer_length))
            self.from_buffer(buffer)
        else:
            self.payload = payload
            self.sequence_number = sequence_number
            self.destination = destination
            if self.payload is None:
                raise ValueError("Payload cannot be None")
            if self.destination > 255 or self.destination < 0:
                raise ValueError("Destination must be 0-255, got %d" % self.destination)
            if self.sequence_number > 2**16-1 or self.sequence_number < 0:
                raise ValueError("Sequence number must be 0-65535, got %d" % self.sequence_number)

    def _pack_header(self,enclosure_length):
        return struct.pack(self._header_format_string,self._valid_start_byte,self._valid_identifier,enclosure_length)

    def to_buffer(self):
        enclosure_length = self.subheader_length + len(self.payload) + self._crc_length
        header = self._pack_header(enclosure_length)
        subheader = struct.pack(self._subheader_format_string,self.sequence_number,self.destination)
        crc_payload = subheader + self.payload
        crc = get_crc(crc_payload)
        footer = struct.pack(self._footer_format_string,crc,self._valid_end_byte)
        return header + crc_payload + footer

    def _unpack_header(self,header):
        start_byte,identifier,length = struct.unpack(self._header_format_string,header)
        if start_byte != self._valid_start_byte:
            raise PacketValidityError("Got invalid start byte 0x%02X" % start_byte)
        if identifier != self._valid_identifier:
            raise PacketValidityError("Got invalid identifier byte 0x%02X" % identifier)
        return length

    def from_buffer(self,buffer):
        length = self._unpack_header(buffer[:self.header_length])
        remainder = buffer[self.header_length:]
        crc_payload = buffer[self.header_length:-self.footer_length]
        self.sequence_number,self.destination = struct.unpack(self._subheader_format_string,remainder[
                                                                                           :self.subheader_length])
        self.payload = remainder[self.subheader_length:-self.footer_length]
        crc,end_byte = struct.unpack(self._footer_format_string,remainder[-self.footer_length:])
        if end_byte != self._valid_end_byte:
            raise PacketValidityError("Got invalid end byte 0x%02X" % end_byte)
        this_crc = get_crc(crc_payload)
        if this_crc != crc:
            raise PacketChecksumError("Bad CRC: got %d, expected %d" % (crc,this_crc))
        if length != len(crc_payload)+2:
            raise PacketLengthError("Bad length:, got %d, expected %d" % (length,len(crc_payload)+2))


class GSECommandPacket(CommandPacket):
    _header_format_table = [('1B','start_byte'),
                            ('1B','link'),
                            ('1B','routing'),
                            ('1B','length'),
                            ]
    _header_format_string = '>' + ''.join([format_ for format_, _ in _header_format_table])
    header_length = struct.calcsize(_header_format_string)
    LOS1 = (0x00, 0x09)
    LOS2 = (0x00, 0x0C)
    TDRSS = (0x01, 0x09)
    IRIDIUM = (0x02, 0x0C)
    _valid_link_tuples = [LOS1, LOS2, TDRSS,IRIDIUM]
    def __init__(self,buffer=None,payload=None,sequence_number=None,destination=None, link_tuple=None):
        if payload is not None:
            if link_tuple not in self._valid_link_tuples:
                raise ValueError("link_tuple %r not valid, valid options are %r" % (link_tuple,self._valid_link_tuples))
            else:
                self.link_tuple = link_tuple
        super(GSECommandPacket,self).__init__(buffer=buffer,payload=payload,sequence_number=sequence_number,
                                              destination=destination)

    def _pack_header(self,enclosure_length):
        return struct.pack(self._header_format_string,self._valid_start_byte,self.link_tuple[0],self.link_tuple[1],
                           enclosure_length)

    def _unpack_header(self,header):
        start_byte,identifier,length = struct.unpack(self._header_format_string,header)
        if start_byte != self._valid_start_byte:
            raise PacketValidityError("Got invalid start byte 0x%02X" % start_byte)
        if identifier != self._valid_identifier:
            raise PacketValidityError("Got invalid identifier byte 0x%02X" % identifier)
        return length

gse_acknowledgment_codes = {0x00: "command transmitted successfully",
                            0x0A: "0x0A: GSE operator disabled science from sending commands",
                            0x0B: "0x0B: Routing address does not match the selected link",
                            0x0C: "0x0C: The link selected was not enabled",
                            0x0D: "0x0D: Some other error"}
def decode_gse_acknowledgement(data):
    if len(data) < 3:
        raise PacketLengthError("GSE Acknowledgement must be 3 bytes, only got %d" % len(data))
    sync1,sync2,ack = struct.unpack('>3B',data[:3])
    if sync1 != 0xFA:
        raise PacketValidityError("GSE Acknowledgement must start with 0xFA, got 0x%02X" % sync1)
    if sync2 != 0xF3:
        raise PacketValidityError("GSE Acknowledgement byte 2 must be 0xF3, got 0x%02X" % sync2)
    if ack not in gse_acknowledgment_codes:
        raise PacketValidityError("GSE Acknowledgement byte not recognized, got 0x%02X" % ack)
    return ack,data[3:]

def encode_gse_acknowledgement(ack_byte):
    return struct.pack('>3B',0xFA,0xF3,ack_byte)
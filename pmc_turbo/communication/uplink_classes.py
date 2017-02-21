import logging
import socket
import struct

from pmc_turbo.communication import constants

logger = logging.getLogger(__name__)


# start_byte = chr(constants.SIP_START_BYTE)
# end_byte = chr(constants.SIP_END_BYTE)

class Uplink():
    def __init__(self, uplink_port):
        self.uplink_port = uplink_port
        # sip_ip='192.168.1.137', sip_port=4001 in our experimental setup.
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_.bind(('0.0.0.0', self.uplink_port))
        socket_.settimeout(0)
        self.uplink_socket = socket_
        self.sip_leftover_buffer = None

    def get_sip_packets(self):
        valid_packets = []
        try:
            data = self.uplink_socket.recv(1024)

            logger.debug('Received bytes on uplink: %r' % data)

            # buffer = self.sip_leftover_buffer + data
            buffer = data
            self.sip_leftover_buffer = ''
            while buffer:
                valid_packet, remainder = process_bytes(buffer)
                logger.debug('Packet is: %r' % valid_packet)
                if valid_packet:
                    valid_packets.append(valid_packet)
                    buffer = remainder
                else:
                    # logger.debug('Did not receive valid packet. Remainder is: %r' % remainder)
                    self.sip_leftover_buffer = remainder
                    break
            return valid_packets
        except socket.error as e:  # This should except a timeouterrror.
            if e.errno != 11:
                pass  # logger.exception(str(e))
            return valid_packets


def process_bytes(buffer, logger=None):
    start_byte = chr(constants.SIP_START_BYTE)
    end_byte = chr(constants.SIP_END_BYTE)
    science_data_request_byte = chr(constants.SCIENCE_DATA_REQUEST_BYTE)
    science_command_byte = chr(constants.SCIENCE_COMMAND_BYTE)
    packet = None
    remainder = buffer
    while buffer:
        idx = buffer.find(start_byte)
        if idx == -1:
            # This means a START_BYTE was not found
            # We are done processing - discard junk before first idx.
            packet, remainder = None, ''
            break
        if not len(buffer) > (idx + 1):
            # Make sure the buffer is long enough...
            packet = None
            remainder = buffer[idx:]
            break
        id_byte = buffer[idx + 1]
        if not id_byte in [science_data_request_byte, science_command_byte]:
            # If the id_byte is not valid, we cut off the junk and continue the loop.
            buffer = buffer[idx + 2:]
            continue
        if id_byte == science_data_request_byte:
            # Science data request
            if logger:
                logger.debug('%d' % len(buffer[idx:]))
            if len(buffer[idx:]) < 3:
                # We are just missing the end byte - throw it in the remainder.
                packet = None
                remainder = buffer[idx:]
                break

            if buffer[idx + 2] == end_byte:
                packet = buffer[idx:idx + 3]
                remainder = buffer[idx + 3:]
                break
            else:
                packet = None
                remainder = buffer[idx + 2:]
                if remainder.find(start_byte) != -1:
                    # If there is another start byte in the buffer, this is junk
                    buffer = remainder
                    continue
                else:
                    break

        if id_byte == science_command_byte:
            if logger:
                logger.debug('Id byte 14 found')
            if len(buffer[idx:]) < 3:
                if logger:
                    logger.debug('Length of buffer insufficient to contain length byte')
                packet = None
                remainder = buffer[idx:]
                break
            length, = struct.unpack('<1B', buffer[idx + 2])
            if len(buffer[idx:]) < (3 + length + 1):
                if logger:
                    logger.debug('Length of buffer insufficient to contain full packet.')
                # We are missing the rest of the packet. Throw it in the remainder.
                packet = None
                remainder = buffer[idx:]
                break

            if buffer[idx + 3 + length] == end_byte:
                if logger:
                    logger.debug('Expected end byte is an end byte.')
                packet = buffer[idx:idx + 3 + length + 1]
                remainder = buffer[idx + 3 + length + 1:]
                break
            else:
                if logger:
                    logger.debug('Expected end byte is NOT an end byte.')
                packet = None
                remainder = buffer[idx + 3:]
                buffer = remainder
                continue
    return packet, remainder

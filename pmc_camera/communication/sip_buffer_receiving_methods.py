from pmc_camera.communication import constants
import struct


# start_byte = chr(constants.SIP_START_BYTE)
# end_byte = chr(constants.SIP_END_BYTE)


def process_bytes(buffer, start_byte, end_byte, logger=None):
    while buffer:
        idx = buffer.find(start_byte)
        if idx == -1:
            # This means a START_BYTE was not found
            # We are done processing - discard junk before first idx.
            return None, ''
        if not len(buffer) > (idx + 1):
            # Make sure the buffer is long enough...
            packet = None
            remainder = buffer[idx:]
            return packet, remainder
        id_byte = buffer[idx + 1]
        if not id_byte in ['\x13', '\x14']:
            # If the id_byte is not valid, we cut off the junk and continue the loop.
            buffer = buffer[idx + 2:]
            continue
        if id_byte == '\x13':
            # Science data request
            if logger:
                logger.debug('%d' % len(buffer[idx:]))
            if len(buffer[idx:]) < 3:
                # We are just missing the end byte - throw it in the remainder.
                packet = None
                remainder = buffer[idx:]
                return packet, remainder

            if buffer[idx + 2] == end_byte:
                packet = buffer[idx:idx + 3]
                remainder = buffer[idx + 3:]
                return packet, remainder
            else:
                packet = None
                remainder = buffer[idx + 2:]
                if remainder.find(start_byte) != -1:
                    # If there is another start byte in the buffer, this is junk
                    buffer = remainder
                    continue
                else:
                    return packet, remainder

        if id_byte == '\x14':
            if logger:
                logger.debug('Id byte 14 found')
            if len(buffer[idx:]) < 3:
                if logger:
                    logger.debug('Length of buffer insufficient to contain length byte')
                packet = None
                remainder = buffer[idx:]
                return packet, remainder
            length, = struct.unpack('<1B', buffer[idx + 2])
            if len(buffer[idx:]) < (3 + length + 1):
                if logger:
                    logger.debug('Length of buffer insufficient to contain full packet.')
                # We are missing the rest of the packet. Throw it in the remainder.
                packet = None
                remainder = buffer[idx:]
                return packet, remainder

            if buffer[idx + 3 + length] == end_byte:
                if logger:
                    logger.debug('Expected end byte is an end byte.')
                packet = buffer[idx:idx + 3 + length + 1]
                remainder = buffer[idx + 3 + length + 1:]
                return packet, remainder
            else:
                if logger:
                    logger.debug('Expected end byte is NOT an end byte.')
                packet = None
                remainder = buffer[idx + 3:]
                buffer = remainder
                continue

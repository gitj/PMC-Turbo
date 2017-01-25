import logging
import struct

logger = logging.getLogger(__name__)

ESCAPE_CHAR = 0xFF


# Since we assign ids to the cameras and attributes, we can just use 255 as our escape character.

class ShortHousekeeping(object):
    def __init__(self, buffer=None):
        self.statuses = {}
        if buffer:
            self.from_buffer(buffer)
        pass

    def from_buffer(self, buffer):
        results = []
        while buffer:
            idx = buffer.find(chr(ESCAPE_CHAR))
            next_idx = buffer[idx + 1:].find(chr(ESCAPE_CHAR))
            if next_idx == -1:
                next_idx = len(buffer)
            bytes = buffer[idx:next_idx + 1]
            format_string = '>1B1B1B%dB' % (len(bytes) - 3)
            unpacked = struct.unpack(format_string, bytes)
            start, id_byte, status_value = unpacked[:3]
            attributes = unpacked[3:]
            self.statuses[id_byte] = (status_value, attributes)
            buffer = buffer[next_idx:]
        return

    def from_values(self, id_bytes, status_value_attribute_tuples):
        for i, id_byte in enumerate(id_bytes):
            self.statuses[id_byte] = status_value_attribute_tuples[i]

    def to_buffer(self):
        buffer = ''
        for key in self.statuses.keys():
            id_byte, status_value, attributes = key, self.statuses[key][0], self.statuses[key][1]
            format_string = '>1B1B1B%dB' % (len(attributes))
            buffer += struct.pack(format_string, ESCAPE_CHAR, id_byte, status_value, *attributes)

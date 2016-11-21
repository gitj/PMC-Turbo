import struct


# These methods will be used by science to decode packets from the SIP and send packets to the SIP


# These methods decode packets sent from the SIP to the science

def decode_packet(packet):
    start_byte, id_byte = struct.unpack('<2B', packet[:2])
    # < makes the packet explicitly little-endian
    end_byte = struct.unpack('<1B', packet[-1])[0]
    message = packet[2:-1]
    if start_byte != 0x10:
        raise RuntimeError("Start byte incorrect")
    if end_byte != 0x03:
        raise RuntimeError("End byte incorrect")
    if id_byte not in packet_dict:
        raise ValueError("Command not in command dict")
    return packet_dict[id_byte](message)


def decode_gps_position(message):
    longitude, latitude, altitude, status = struct.unpack('<3f1B', message)
    return dict(title='gps_position', longitude=longitude, latitude=latitude,
                altitude=altitude, status=status)


def decode_gps_time(message):
    time_of_week, week_number, time_offset, cpu_time = struct.unpack('<1f1h2f', message)
    return dict(title='gps_time', time_of_week=time_of_week, week_number=week_number,
                time_offset=time_offset, cpu_time=cpu_time)


def decode_mks_pressure_altitude(message):
    high, mid, low = struct.unpack('<3h', message)
    return dict(title='mks_pressure_altitude', high=high, mid=mid, low=low)


def decode_science_data_request(message):
    # Note that decode_science_data_request, the message is an empty string
    # I still need to decide how to handle this.
    return dict(title='science_data_request')


def decode_science_command(message):
    # I am deciding that the message should have the following format:
    # 1Bxs where the first byte is "which camera"
    format_string = '<%ds' % (len(message))
    # -2 because -1 byte for len, -1 byte for which
    value, = struct.unpack(format_string, message)
    # Comma is necessary because the struct.unpack returns a tuple.
    return dict(value=value, title='science_data_command')


# These methods are to be sent to the SIP as a request for something.

def construct_gps_position_request_packet():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('<3B', 0x10, 0x50, 0x03)


def construct_gps_time_request_packet():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('<3B', 0x10, 0x51, 0x03)


def construct_mks_altitude_request_packet():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('<3B', 0x10, 0x52, 0x03)


def construct_science_data_packet(data):
    if not 1 <= len(data) <= 255:
        raise ValueError("Data length must be between 1 and 255.")
    # format_string = '3B%dh' % data_length
    # return struct.pack(format_string, 0x10, 0x53, data_length, *data)
    # This passes in as arguments all of the values in an array.
    # It may be easier to use strings instead - convert data to string before passing it in.
    format_string = '<3B%ds1B' % len(data)
    return struct.pack(format_string, 0x10, 0x53, len(data), data, 0x03)


packet_dict = {
    0x10: decode_gps_position,
    0x11: decode_gps_time,
    0x12: decode_mks_pressure_altitude,
    0x13: decode_science_data_request,
    0x14: decode_science_command,
}

import struct



## These commands and responses will be sent from the science computer to the LDB comm computer.

def construct_gps_position_request():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('3B', 0x10, 0x50, 0x03)


def construct_gps_time_request():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('3B', 0x10, 0x51, 0x03)


def construct_mks_altitude_request():
    # 0x10 is ascii.dle, which every message needs to start with.
    # 0x03 is ascii.etx, the terminator
    return struct.pack('3B', 0x10, 0x52, 0x03)

def construct_science_data(data):
    data_length = len(data)
    if not 1 <= data_length <= 255:
        raise ValueError("Data length must be between 1 and 255.")
    #byte_length_string = '3B%dh' % data_length
    #return struct.pack(byte_length_string, 0x10, 0x53, data_length, *data)
    # This passes in as arguments all of the values in an array.
    # It may be easier to use strings instead - convert data to string before passing it in.
    byte_length_string = '3B%ds1B' % data_length
    return struct.pack(byte_length_string, 0x10, 0x53, data_length, data, 0x03)


## These commands and responses will be sent from the LDB comm computer to the science computer.


def construct_gps_position(longitude, latitude, altitude, satellite_status):
    # longtidue, latitude, altitude are 4-byte IEEEstd 754 single-precision rela-format numbers
    # long and lat are in degrees, alt is in meters.
    # All are little-endian
    # Status is a single byte.
    return struct.pack('2B4h4h4h2B', 0x10, 0x10, longitude, latitude, altitude, satellite_status, 0x03)


def construct_gps_time(time_week, week_number, gps_time_offset, cpu_time):
    return struct.pack('2B4h2h4h4h1B', 0x10, 0x11, time_week, week_number,
                       gps_time_offset, cpu_time, 0x03)
    # Assumed that cpu_time is a 4 byte real number like time of week and gps_time_offset
    # However the manual doesn't explicity say what type it is.


def construct_mks_pressure_altitude(high, mid, low):
    return struct.pack('2B2h2h2h1B', 0x10, 0x12, high, mid, low, 0x03)
    # The LDB payload engineer will provide the switch points to use so reader knows
    # which sensor to use.
    # Manual is ambiguous, but I believe all measurements are sent regardless.


def construct_science_request():
    return struct.pack('3B', 0x10, 0x13, 0x03)


def construct_science_command(command):
    byte_length_string = '3B%ds1B' % len(command)
    return struct.pack(byte_length_string, 0x10, 0x14, len(command), command, 0x03)

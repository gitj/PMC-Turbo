import struct



def get_command_from_struct(mystruct):
    start_byte, command = stuct.unpack('2B', mystruct[:2])
    end_byte = struct.unpack('1B', mystruct[-1])[0]
    if start_byte != 0x10:
        raise RuntimeErrore("Start byte incorrect")
    if end_byte != 0x03:
        raise RuntimeError("End byte incorrect")
    if command not in command_dict:
        raise ValueError("Command not in command dict")
    return command_dict[command]


def handle_gps_position(mystruct):
    start, id_byte, longitude, latitude, altitude, status, end = struct.unpack('2B3f2B', mystruct)
    return longitude, latitude, altitude, status


def handle_gps_time(mystruct):
    start, id_byte, time_of_week, week_number, time_offset, cpu_time, end = struct.unpack('2B1f1h2f1B', mystruct)
    return time_of_week, week_number, time_offset, cpu_time


def handle_mks_pressure_altitude(mystruct):
    start, id_byte, high, mid, low, end = struct.unpack('2B3h2B', mystruct)
    return high, mid, low


# Need to actually write these functions
def handle_request_science_data():
    # This will be complicated
    # It either needs to decide beforehand what science data to send down
    # Or decide when this is called.
    return
def handle_science_command():
    # Figure out which command has been sent, execute it.
    return

def handle_request_gps_position():
    return
def handle_request_gps_time():
    return
def handle_request_altitude():
    return
# We don't really need to worry about these - the SIP should deal with them already
# Make sure this is correct.


command_dict = {
                0x10: handle_gps_position,
                0x11: handle_gps_time,
                0x12: handle_mks_pressure_altitude,
                0x13: handle_request_science_data,
                0x14: handle_science_command,
                0x50: handle_request_gps_position,
                0x51: handle_request_gps_time,
                0x52: handle_request_altitude,
                0x53: handle_request_science_data
               }

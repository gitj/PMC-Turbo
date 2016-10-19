import numpy as np
from sip_packet_generator import *
from sip_packet_receiver import *

if __name__ == "__main__":
    packet = construct_gps_position_request()
    command = get_command_from_struct(packet)
    print command(packet)

    packet = construct_gps_time_request()
    command = get_command_from_struct(packet)
    print command(packet)

    packet = construct_mks_altitude_request()
    command = get_command_from_struct(packet)
    print command(packet)

    #np.random.seed(0)
    #random_data = np.random.randint(0, 255, size = 255, dtype='uint8')
    #packet = construct_science_data(random_data.tostring())
    #deconstruct = struct.unpack('3B255s1B', packet)
    #print deconstruct

    packet = construct_gps_position(1.0, 2.0, 3.0, 1)
    command = get_command_from_struct(packet)
    print command(packet)

    packet = construct_gps_time(1.0, 1, 2.0, 3.0)
    command = get_command_from_struct(packet)
    print command(packet)


    packet = construct_mks_pressure_altitude(1, 2, 3)
    command = get_command_from_struct(packet)
    print command(packet)

    packet = construct_science_request()
    command = get_command_from_struct(packet)
    print command(packet)

    packet = construct_science_command('test')
    command = get_command_from_struct(packet)
    print command(packet)

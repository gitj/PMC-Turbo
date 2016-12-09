import numpy as np
from pmc_camera.communication import SIP_communication_simulator
from pmc_camera.communication import science_communication


def test_gps_position_packet():
    packet = SIP_communication_simulator.construct_gps_position_packet(1.,1.,1.,1)
    decoded_packet = science_communication.decode_packet(packet)
    predicted_result = dict(title='gps_position', longitude=1., latitude=1., altitude=1., status=1)
    assert(decoded_packet == predicted_result)


def test_gps_time_packet():
    packet = SIP_communication_simulator.construct_gps_time_packet(1., 1, 1., 1.)
    decoded_packet = science_communication.decode_packet(packet)
    predicted_result = dict(title='gps_time', time_of_week=1., week_number=1, time_offset=1., cpu_time=1.)
    assert(decoded_packet == predicted_result)


def test_gps_mks_pressure_altitude():
    packet = SIP_communication_simulator.construct_mks_pressure_altitude_packet(1, 1, 1)
    decoded_packet = science_communication.decode_packet(packet)
    predicted_result = dict(title='mks_pressure_altitude', high=1, mid=1, low=1)
    assert(decoded_packet == predicted_result)


def test_science_data_request():
    packet = SIP_communication_simulator.construct_science_request_packet()
    decoded_packet = science_communication.decode_packet(packet)
    predicted_result = {}
    assert(decoded_packet == predicted_result)


def test_science_command_packet():
    packet = SIP_communication_simulator.construct_science_command_packet('0', 'test', '')
    decoded_packet = science_communication.decode_packet(packet)
    predicted_result = dict(which='0', command='test', value='', title='science_data_command')
    # Going to need to add value
    assert(decoded_packet == predicted_result)
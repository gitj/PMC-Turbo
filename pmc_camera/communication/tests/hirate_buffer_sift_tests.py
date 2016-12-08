import unittest
import numpy as np
import struct
from pmc_camera.communication import constants
from pmc_camera.communication.hirate import hirate_sending_methods, hirate_receiving_methods, cobs_encoding


class HirateBufferSiftTests(unittest.TestCase):
    def setUp(self):
        return

    def tearDown(self):
        return

    def empty_packet_test(self):
        buffer = '\xfa\xff\x01\x00\x00\x00\x01'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '')
        assert (sip_packets == ['\xfa\xff\x01\x00\x00\x00\x01'])

    def sip_packet_in_data_test(self):
        buffer = '\xfa\xff\x01\x00\x00\x00\x01'
        np.random.seed(0)
        random_msg = np.random.randint(0, 255, size=10000).astype('uint8')
        encoded_data = cobs_encoding.encode_data(random_msg, escape_character=constants.SYNC_BYTE)
        buffer = encoded_data[:(len(encoded_data) / 2)] + buffer + encoded_data[(len(encoded_data) / 2):]
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == encoded_data)
        assert (sip_packets == ['\xfa\xff\x01\x00\x00\x00\x01'])

    def false_start_test(self):
        buffer = '\xfa\xfa\xff\x01\x00\x00\x00\x01'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa')
        assert (sip_packets == ['\xfa\xff\x01\x00\x00\x00\x01'])

    def insufficient_length_for_length_byte_test(self):
        buffer = '\xfa\xff\x01'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa\xff\x01')
        assert (sip_packets == [])

    def insufficient_length_for_length_byte_test(self):
        buffer = '\xfa\xff\x01\x00\x00\x03\x00'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa\xff\x01\x00\x00\x03\x00')
        assert (sip_packets == [])

    def bad_id_byte_test(self):
        buffer = '\xfa\x99\x01\x00\x00\x00\x01'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa\x99\x01\x00\x00\x00\x01')
        assert (sip_packets == [])

    def no_end_test(self):
        buffer = '\xfa\xff\x01\x00\x00\x00'
        # A bit confused about where this goes - I thought it fails on length but that doesn't look covered
        # it work but follow it step by step.
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa\xff\x01\x00\x00\x00')
        assert (sip_packets == [])

    def bad_checksum_test(self):
        buffer = '\xfa\xff\x01\x00\x00\x00\x07'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        assert (filtered_buffer == '\xfa\xff\x01\x00\x00\x00\x07')
        assert (sip_packets == [])

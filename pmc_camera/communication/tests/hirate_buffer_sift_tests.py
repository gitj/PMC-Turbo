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
        print '%r' % encoded_data
        buffer = encoded_data[:(len(encoded_data) / 2)] + buffer + encoded_data[(len(encoded_data) / 2):]
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        print '%r' % filtered_buffer
        assert (filtered_buffer == encoded_data)
        assert (sip_packets == ['\xfa\xff\x01\x00\x00\x00\x01'])

    def false_start_test(self):
        buffer = '\xfa\xfa\xff\x01\x00\x00\x00\x01'
        filtered_buffer, sip_packets = hirate_receiving_methods.find_sip_packets_in_buffer(buffer)
        print '%r' % filtered_buffer
        print '%r' % sip_packets[0]
        assert (filtered_buffer == '\xfa')
        assert (sip_packets == ['\xfa\xff\x01\x00\x00\x00\x01'])

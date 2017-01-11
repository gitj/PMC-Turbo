import unittest
from pmc_camera.communication.uplink_classes import process_bytes


class BufferInterpretationTests(unittest.TestCase):
    def setUp(self):
        return

    def tearDown(self):
        return

    def test_empty_buffer(self):
        buffer = ''
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_science_request(self):
        buffer = '\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_solo_start_byte(self):
        buffer = '\x10'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10')

    def test_separated_science_request_packet(self):
        buffer = '\x10\x13'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x13')

    def test_separated_science_command_packet(self):
        buffer = '\x10\x14'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x14')

    def test_truncated_science_command_packet(self):
        buffer = '\x10\x14\x06'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x14\x06')

    def test_good_science_command_byte(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x03')
        self.assertEqual(remainder, '')

    def test_lost_end1(self):
        buffer = '\x10\x14\x06\x00\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x14\x06\x00\x10\x13\x03')

    def test_science_in_middle_valid_end_byte(self):
        buffer = '\x10\x14\x06\x00\x10\x13\x03\x00\x00\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x14\x06\x00\x10\x13\x03\x00\x00\x03')
        self.assertEqual(remainder, '')

    def test_science_request_in_middle_invalid_end_byte(self):
        buffer = '\x10\x14\x06\x00\x10\x13\x03\x00\x00\x55'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '\x00\x00\x55')

    def test_lost_end2(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_lost_end3(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_lost_end_no_byte(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_crap_at_beginning(self):
        buffer = '\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_no_start_byte(self):
        buffer = '\x00\x00\x00\x00'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_bad_id(self):
        buffer = '\x10\x26\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_bad_end_byte_science_request(self):
        buffer = '\x10\x13\x00'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x00')

    def test_bad_end_byte_science_request_another_byte(self):
        buffer = '\x10\x13\x10\x13\x03'
        packet, remainder = process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

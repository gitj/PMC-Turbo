import unittest
from pmc_camera.communication import camera_communicator

class BufferInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.c = camera_communicator.Communicator(0, run_pyro=True)

    def tearDown(self):
        self.c.__del__()

    def test_science_request(self):
        buffer = '\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_solo_start_byte(self):
        buffer = '\x10'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10')

    def test_separated_science_request_packet(self):
        buffer = '\x10\x13'
        packet, remainder = self.c.process_bytes(buffer)
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x13')

    def test_separated_science_command_packet(self):
        buffer = '\x10\x14'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x14')

    def test_truncated_science_command_packet(self):
        buffer = '\x10\x14\x06'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x14\x06')

    def test_good_science_command_byte(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x03')
        self.assertEqual(remainder, '')

    def test_lost_end1(self):
        buffer = '\x10\x14\x06\x00\x00\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_lost_end2(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_lost_end3(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_crap_at_beginning(self):
        buffer = '\x00\x00\x00\x00\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_no_start_byte(self):
        buffer = '\x00\x00\x00\x00'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_bad_id(self):
        buffer = '\x10\x26\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '')

    def test_bad_end_byte_science_request(self):
        buffer = '\x10\x13\x00'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x00')

    def test_bad_end_byte_science_request_another_byte(self):
        buffer = '\x10\x13\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')
import unittest
from pmc_camera.communication import camera_communicator

class TwoCommunicatorTests(unittest.TestCase):
    def setUp(self):
        self.c = camera_communicator.Communicator(0, run_pyro=True)

    def tearDown(self):
        self.c.__del__()

    def test_science_request(self):
        buffer = '\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_science_request(self):
        buffer = '\x10\x13\x03'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, '\x10\x13\x03')
        self.assertEqual(remainder, '')

    def test_separated_science_request_packet(self):
        buffer = '\x10'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10')
        buffer = '\x10\x13'
        packet, remainder = self.c.process_bytes(buffer)
        self.assertEqual(packet, None)
        self.assertEqual(remainder, '\x10\x13')
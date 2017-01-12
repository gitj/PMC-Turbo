import unittest
import socket
from pmc_camera.communication import camera_communicator


class FakeLowrateUplink():
    def __init__(self):
        self.bytes = ''

    def assign_bytes_to_get(self, bytes):
        self.bytes = bytes

    def get_sip_packets(self):
        return [self.bytes]


class FakeLowrateDownlink():
    def send(self, msg):
        self.buffer = msg

    def retrieve_msg(self):
        return self.buffer


class NoPeersTest(unittest.TestCase):
    def setUp(self):
        self.c = camera_communicator.Communicator(cam_id=0, peers=[], controller=None)

    def tearDown(self):
        self.c.close()

    def setup_leader_attributes_test(self):
        UPLINK_PORT = 4001
        LOWRATE_DOWNLINK_IP = 'localhost'
        LOWRATE_DOWNLINK_PORT = 4001
        HIRATE_DOWNLINK_IP = 'localhost'
        HIRATE_DOWNLINK_PORT = 4002
        DOWNLINK_SPEED = 700

        self.c.setup_leader_attributes(UPLINK_PORT, LOWRATE_DOWNLINK_PORT, LOWRATE_DOWNLINK_IP,
                                       HIRATE_DOWNLINK_IP, HIRATE_DOWNLINK_PORT, DOWNLINK_SPEED)

    def get_bytes_test(self):
        self.c.lowrate_uplink = FakeLowrateUplink()
        self.c.lowrate_uplink.assign_bytes_to_get('\x10\x13\x03')
        valid_packets = self.c.lowrate_uplink.get_sip_packets()
        assert (valid_packets == ['\x10\x13\x03'])

    #def get_and_process_bytes_test(self):
        '''
        UPLINK_PORT = 4001
        LOWRATE_DOWNLINK_IP = '0.0.0.0'
        LOWRATE_DOWNLINK_PORT = 4001
        HIRATE_DOWNLINK_IP = '0.0.0.0'
        HIRATE_DOWNLINK_PORT = 4002
        DOWNLINK_SPEED = 700

        self.c.setup_leader_attributes(UPLINK_PORT, LOWRATE_DOWNLINK_PORT, LOWRATE_DOWNLINK_IP,
                                       HIRATE_DOWNLINK_IP, HIRATE_DOWNLINK_PORT, DOWNLINK_SPEED)

        sip_bytes_to_process = '\x10\x13\x03'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(sip_bytes_to_process, ('0.0.0.0', UPLINK_PORT))
        sock.close()
                '''

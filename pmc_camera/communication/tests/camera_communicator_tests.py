import unittest
import socket
from pmc_camera.communication import camera_communicator
from pmc_camera.communication import packet_classes,command_table
from pmc_camera.pipeline import controller

def test_valid_command_table():
    cc = camera_communicator.Communicator(cam_id=0,peers=[],controller=None,start_pyro=False)
    cc.validate_command_table()

def test_basic_command_path():
    cont = controller.Controller(None)
    cc1 = camera_communicator.Communicator(cam_id=0,peers=[],controller=cont,start_pyro=False)
    cc2 = camera_communicator.Communicator(cam_id=1,peers=[],controller=cont,start_pyro=False)
    cc1.peers = [cc1,cc2]
    cc1.destination_lists = {0:[cc1],1:[cc2]}
    command = command_table.command_manager.set_focus(focus_step=1000)
    command_packet = packet_classes.CommandPacket(payload=command,sequence_number=1,destination=1)
    cc1.execute_packet(command_packet.to_buffer())


    bad_buffer = command_packet.to_buffer()[:-2] + 'AA'
    cc1.execute_packet(bad_buffer)

    bad_crc_buffer = command_packet.to_buffer()[:-2] + 'A\x03'
    cc1.execute_packet(bad_crc_buffer)

    cc1.execute_packet('bad packet')

    non_existant_command = '\xfe' + command
    cc1.execute_packet(packet_classes.CommandPacket(payload=non_existant_command,sequence_number=1,
                                                                    destination=1).to_buffer())




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

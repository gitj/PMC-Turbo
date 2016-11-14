import socket
import unittest
from pmc_camera.communication import camera_communicator, science_communication, SIP_communication_simulator
from pmc_camera.pipeline import basic_pipeline


class TwoCommunicatorTests(unittest.TestCase):
    def setUp(self):
        self.communicator0 = camera_communicator.Communicator(0)
        self.communicator1 = camera_communicator.Communicator(1)

    def tearDown(self):
        self.communicator0.end_loop = True
        self.communicator1.end_loop = True
        self.communicator0.__del__()
        self.communicator1.__del__()

    def test_initial_master_decision(self):
        self.communicator0.identify_leader()
        self.communicator1.identify_leader()
        self.assertEqual(self.communicator0.leader_handle, self.communicator0.peers[0])
        self.assertEqual(self.communicator1.leader_handle, self.communicator1.peers[0])
        self.assertEqual(self.communicator0.leader_handle, self.communicator1.leader_handle)

    def test_pings(self):
        assert (self.communicator0.ping_other(self.communicator0.peers[1]) == True)
        assert (self.communicator1.ping_other(self.communicator0.peers[0]) == True)


class OneCommunicatorTests(unittest.TestCase):
    def setUp(self):
        self.communicator = camera_communicator.Communicator(0)
        self.communicator.setup_leader_attributes(sip_ip='localhost', sip_port=4001)

    def tearDown(self):
        self.communicator.end_loop = True
        self.communicator.__del__()

    def test_receive_sip_message(self):
        sip_simulator_port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sip_packet = SIP_communication_simulator.construct_science_request_packet()
        sip_simulator_port.sendto(sip_packet, ('localhost', 4001))
        self.communicator.get_bytes_from_sip_socket()
        assert (self.communicator.sip_packet_decoder.buffer == sip_packet)


'''
def process_packet(packet):
    return
    # camera_communicator.Communicator(0)
    # communicator0.packet_queue.put(packet)
    # communicator0.process_packet()
    # Assert packet is as expected


def process_command_queue(command):
    return
    # communicator0 = camera_communicator.Communicator(0)
    # communicator0.command_queue.put(command)
    # communicator0.check_command_queue()
    # Assert this works


# Design question: should pipeline be an attribute of communicator (e.g. communicator0.pipeline)?

def test_image_capture():
    return
    # assert (images as expected)
'''

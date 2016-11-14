import socket
from pmc_camera.communication import camera_communicator, science_communication, SIP_communication_simulator
from pmc_camera.pipeline import basic_pipeline


def test_initial_master_decision():
    communicator0 = camera_communicator.Communicator(0)
    communicator1 = camera_communicator.Communicator(1)
    communicator0.start_pyro_thread()
    communicator1.start_pyro_thread()

    communicator0.identify_leader()
    communicator1.identify_leader()
    assert (communicator0.leader_handle == communicator0.peers[0])
    assert (communicator1.leader_handle == communicator1.peers[0])
    assert (communicator0.leader_handle == communicator0.leader_handle)

    communicator0.end_loop = True
    communicator1.end_loop = True
    communicator0.__del__()
    communicator1.__del__()


def test_pings():
    communicator0 = camera_communicator.Communicator(0)
    communicator1 = camera_communicator.Communicator(1)
    communicator0.start_pyro_thread()
    communicator1.start_pyro_thread()

    assert (communicator0.ping_other(communicator0.peers[1]) == True)
    assert (communicator1.ping_other(communicator0.peers[0]) == True)

    communicator0.end_loop = True
    communicator1.end_loop = True
    communicator0.__del__()
    communicator1.__del__()


def test_setup_sip_port(sip_ip='localhost', sip_port=4001):
    # sip_ip='192.168.1.137', sip_port=4001
    communicator0 = camera_communicator.Communicator(0)

    communicator0.setup_leader_attributes(sip_ip, sip_port)

    communicator0.end_loop = True
    communicator0.__del__()


def test_receive_sip_message(sip_ip='localhost', sip_port=4001):
    sip_simulator_post = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    communicator0 = camera_communicator.Communicator(0)
    communicator0.setup_leader_attributes(sip_ip, sip_port)

    sip_packet = SIP_communication_simulator.construct_science_request_packet()

    sip_simulator_post.sendto(sip_packet, (sip_ip, sip_port))

    communicator0.get_bytes_from_sip_socket()
    communicator0.__del__()

    # print sip_packet
    # print communicator0.sip_packet_decoder.buffer
    # print sip_packet == communicator0.sip_packet_decoder.buffer

    assert (communicator0.sip_packet_decoder.buffer == sip_packet)
    # Need to figure out a way to put the bytes I want in here - set up socket
    # assert(results of command)


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

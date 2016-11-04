import zmq
import socket
import time
import science_communication
import sip_packet_decoder
import Queue


class Communicator():
    def __init__(self, base_port, cam_id, sip_ip, sip_port):
        # sip_ip='192.168.1.137', sip_port=4001 in our experimental setup.
        self.base_port = base_port
        self.cam_id = cam_id
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://*:%s" % str(self.base_port + self.cam_id))
        self.other_camera_sockets = []
        self.master = None
        self.kvdb = dict(value=4.6)
        self.command_dict = dict(give_kvdb=self.send_kvdb)
        self.packet_queue = Queue.Queue()
        self.command_queue = Queue.Queue()
        self.setup_sip_socket(sip_ip, sip_port)
        self.sip_packet_decoder = sip_packet_decoder.SIPPacketDecoder()

    ### SIP socket methods

    def setup_sip_socket(self, sip_ip, sip_port):
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_.bind((sip_ip, sip_port))
        socket.timeout = 0
        self.sip_socket = socket_

    def get_bytes_from_sip_socket(self):
        self.sip_socket.timeout = 0
        while data is not None:
            data = self.sip_socket.recv(1024)
            self.sip_packet_decoder.buffer.append(data)

    def get_bytes_and_process(self):
        self.get_bytes_from_socket()
        self.sip_packet_decoder.process_buffer()
        self.sip_packet_decoder.process_candidate_packets()

    ### ZMQ methods to connect with other cameras

    def connect_to_other_cameras(self, num_cameras):
        for i in range(num_cameras):
            if i != self.cam_id:
                new_socket = self.context.socket(zmq.PAIR)
                new_socket.connect("tcp://localhost:%s" % (self.base_port + i))
                self.other_camera_sockets.append(new_socket)
                # Switch to a list of ports that will be assigned to camera.

    def send_kvdb(self):
        self.socket.send_json(self.kvdb)

    def determine_master(self):
        # Look for Camera_Controller with higher number, if none exists, I am the master.
        return

    def listen_for_command(self):
        while True:
            if self.socket.poll(timeout=0):
                command = self.socket.recv()
                if command in self.command_dict:
                    self.command_dict[command]()
            time.sleep(0.1)

    def get_other_camera_info(self):
        for socket in self.other_camera_sockets:
            kvdb = self.request_kvdb(socket)

    def send_command(self, command, other_camera_socket):
        other_camera_socket.send(command)

    def check_packet_queue(self):
        if not self.packet_queue.empty():
            packet = self.packet_queue.get()
            packet_dict = science_communication.decode_packet(packet)
            self.process_packet(packet_dict)

    def process_packet(self, packet_dict):
        if packet_dict['title'] == 'science_data_command':
            self.command_queue.put((packet_dict['which'], packet_dict['command'], packet_dict['value']))
        if packet_dict['title'] == 'science_data_request':
            self.command_queue.put((self.cam_id, 'answer_data_request', 0))
        else:
            self.kvdb[packet_dict['title']] = packet_dict

    def check_command_queue(self):
        if not self.command_queue.empty():
            command = self.command_queue.get()
            if command['title'] in self.command_dict:
                self.command_dict[command['title']](command['which'], command['value'])

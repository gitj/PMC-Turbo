import zmq
import socket
import time
import science_communication
import sip_packet_decoder
import Queue


class Communicator():
    def __init__(self, base_port, cam_id):
        self.base_port = base_port
        self.cam_id = cam_id
        self.context = zmq.Context()
        self.zmq_socket = self.context.socket(zmq.PAIR)
        self.kvdb = dict(value=4.6)
        self.command_dict = dict(give_kvdb=self.send_kvdb)
        self.command_queue = Queue.Queue()

        self.ping = dict(cam_id=self.cam_id, msg='ping')
        # Change this to be a standard message sent to master.
        self.ping_response = dict(cam_id=self.cam_id, msg='ping_response')
        # master should give a ping response here

    def set_up_master_attributes(self, sip_ip, sip_port):
        self.packet_queue = Queue.Queue()
        self.ping_queue = Queue.Queue()
        self.setup_sip_socket(sip_ip, sip_port)
        self.sip_packet_decoder = sip_packet_decoder.SIPPacketDecoder()
        self.peers = {}
        # Format of peers: {cam_id: zmq_socket}

    ### Loops to continually be run

    def run_peer_tasks(self):
        self.identify_master()
        self.look_for_messages()
        self.process_command_queue()
        self.reconcile_kvdb_and_pipeline()

    def run_master_tasks(self):
        self.answer_pings()
        self.process_sip_socket()
        self.process_packet_queue()

    ### Master methods

    def populate_peers(self, num_cameras):
        # Makes a dict of all the peers and a socket for each.
        for i in range(num_cameras):
            new_socket = self.context.socket(zmq.PAIR)
            new_socket.connect("tcp://localhost:%s" % (self.base_port + i))
            # Change from localhost eventually.
            self.peers[i] = new_socket

    def answer_pings(self):
        while self.zmq_socket.poll(timeout=0):
            ping = self.zmq_socket.recv_json()
            self.ping_queue.put(ping)
        while not self.ping_queue.empty():
            self.respond_to_ping(self.ping_queue.get())

    def respond_to_ping(self, ping):
        # If the ping is a ping, find the zmq_socket in self.peers and send the generic ping_response
        if ping['msg'] == 'ping':
            self.peers[ping['cam_id']].send_json(self.ping_response)

    def process_packet_queue(self):
        while not self.packet_queue.empty():
            packet = self.packet_queue.get()
            packet_dict = science_communication.decode_packet(packet)
            self.process_packet(packet_dict)

    def process_packet(self, packet_dict):
        # I need to think about the format of packets and how to deal with them.
        return

    ##### SIP socket methods

    def setup_sip_socket(self, sip_ip, sip_port):
        # sip_ip='192.168.1.137', sip_port=4001 in our experimental setup.
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_.bind((sip_ip, sip_port))
        socket.timeout = 0
        self.sip_socket = socket_

    def get_bytes_from_sip_socket(self):
        self.sip_socket.timeout = 0
        done = False
        while not done:
            data = self.sip_socket.recv(1024)
            if data:
                self.sip_packet_decoder.buffer.append(data)
            else:
                done = True

    def interpret_bytes_from_sip_socket(self):
        self.sip_packet_decoder.process_buffer()
        self.sip_packet_decoder.process_candidate_packets()
        self.packet_queue.put(self.sip_packet_decoder.confirmed_packets)

    def process_sip_socket(self):
        self.get_bytes_from_sip_socket()
        self.interpret_bytes_from_sip_socket()

    ### peer methods

    def process_command_queue(self):
        while not self.command_queue.empty():
            command = self.command_queue.get()
            self.run_command(command)

    def run_command(self, command):
        if command in self.command_dict:
            self.command_dict[command]

    def identify_master(self):
        if self.master:
            self.ping_master()
        if not self.master:
            self.determine_master()

    def ping_master(self):
        self.master.zmq_socket.send_json(self.ping)
        ### Semd to master socket rather than own socket
        result = self.get_ping_response()
        if not result:
            self.determine_master()

    def look_for_messages(self):
        while self.zmq_socket.poll(timeout=0):
            message = self.zmq_socket.recv_json()
            self.process_message(message)

    def process_message(self):
        # If it is a ping back I want to let myself know I received a response
        # If it is a command I want to put it in the command queue
        # If it is junk I want to discard it.
        return

    def get_ping_response(self):
        pingback = self.zmq_socket.recv_json()
        if pingback != self.expected_pingback:
            return False
        return True

    # Decide how to do this - I don't want a wait.
    # I think I want to check if the master pinged back last time I checked - a queue?

    def determine_master(self):
        # ping all the addresses where lower cam ids should live, in order of priority
        # If response, set master
        # if no response, set self as master.
        return

    def reconcile_kvdb_and_pipeline(self):
        if self.kvdb != self.pipeline.status:
            self.pipeline.change_parameters(self.kvdb)
            # These functions need to be written for the pipeline

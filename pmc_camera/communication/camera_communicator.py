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
        self.ping_response = None
        # master should give a ping response here

    def set_up_master_attributes(self, sip_ip, sip_port):
        self.packet_queue = Queue.Queue()
        self.ping_queue = Queue.Queue()
        self.setup_sip_socket(sip_ip, sip_port)
        self.sip_packet_decoder = sip_packet_decoder.SIPPacketDecoder()

    ### Loops to continually be run

    def run_slave_loop(self):
        self.identify_master()
        self.process_command_queue()
        self.reconcile_kvdb_and_pipeline()

    def run_master_loop(self):
        self.process_sip_socket()
        self.process_packet_queue()
        self.answer_pings()

    ### Master methods

    def answer_pings(self):
        while self.zmq_socket.poll(timeout=0):
            ping = self.zmq_socket.recv_json()
            self.ping_queue.put(ping)
        while len(self.ping_queue) != 0:
            self.respond_to_ping(self.ping_queue.get())

    def respond_to_ping(self, ping):
        # Fill this in
        return

    def process_packet_queue(self):
        while len(self.packet_queue) != 0:
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
        while data is not None:
            data = self.sip_socket.recv(1024)
            self.sip_packet_decoder.buffer.append(data)

    def interpret_bytes_from_sip_socket(self):
        self.sip_packet_decoder.process_buffer()
        self.sip_packet_decoder.process_candidate_packets()
        self.packet_queue.put(self.sip_packet_decoder.confirmed_packets)

    def process_sip_socket(self):
        self.get_bytes_from_sip_socket()
        self.interpret_bytes_from_sip_socket()

    ### Slave methods

    def process_command_queue(self):
        while len(self.command_queue) != 0:
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
        self.zmq_socket.send_json(self.ping)
        self.get_ping_response()
        if not self.ping_response:
            self.determine_master()

    def get_ping_response(self):
        return

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

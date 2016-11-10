import zmq
import socket
import time
import science_communication
import sip_packet_decoder
import Queue
import Pyro4, Pyro4.socketutil, Pyro4.errors
import select
import threading

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.COMMTIMEOUT = 1.0
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

base_port = 40000  # Change this const when a base port is decided upon.
num_cameras = 2
ip_list = ['192.168.1.137'] * num_cameras
port_list = [base_port + i for i in range(num_cameras)]  # Ditto for the IP list and ports.


@Pyro4.expose
class Communicator():
    def __init__(self, cam_id):
        self.port = base_port + cam_id
        self.cam_id = cam_id
        self.kvdb = dict(value=4.6)
        self.command_dict = {}
        # dict(give_kvdb=self.send_kvdb)
        self.command_queue = Queue.Queue()
        self.leader_handle = None
        self.peers = []
        self.end_loop = False

        self.daemon = None
        self.sip_socket = None
        # We will instantiate these later

        self.setup_pyro()
        self.get_communicator_handles(ip_list, port_list)

    def __del__(self):
        if self.daemon:
            self.daemon.shutdown()
        if self.sip_socket:
            self.sip_socket.close()

    def setup_pyro(self):
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=self.port)
        uri = self.daemon.register(self, "communicator")
        print uri

    def setup_leader_attributes(self, sip_ip, sip_port):
        self.packet_queue = Queue.Queue()
        self.setup_sip_socket(sip_ip, sip_port)
        self.sip_packet_decoder = sip_packet_decoder.SIPPacketDecoder()
        # Format of peers: {cam_id: zmq_socket}

    def get_communicator_handles(self, ip_list, port_list):
        # The ip_list and port_list are lists of strings for the ip addresses and ports where the communicators live.
        # Grabs all the other peers.
        for i in range(len(ip_list)):
            peer_handle = Pyro4.Proxy('PYRO:communicator@%s:%s' % (ip_list[i], port_list[i]))
            self.peers.append(peer_handle)

    ### Loops to continually be run

    def run_peer_tasks(self):
        self.identify_leader()
        #self.run_pyro_tasks()
        self.reconcile_kvdb_and_pipeline()

    def run_leader_tasks(self):
        #elf.run_pyro_tasks()
        self.process_sip_socket()
        self.process_packet_queue()

    def start_pyro_thread(self):
        pyro_thread = threading.Thread(target=self.pyro_loop)
        pyro_thread.start()

    def pyro_loop(self):
        while True:
            self.run_pyro_tasks()
            if self.end_loop == True:
                # Switch this to end the pyro loop.
                return
            time.sleep(0.01)

    def run_pyro_tasks(self):
        # Bug: first time this is run it doesn't do anything.
        # Subsequent runs work.
        events, _, _ = select.select(self.daemon.sockets, [], [], 0)
        if events:
            self.daemon.events(events)
            # else:
            #    time.sleep(0.001)

    ### leader methods


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

    def ping(self):
        return True

    def ping_other(self, camera_handle):
        # Need to add timeout to this, as well as a case for no ping.
        try:
            ping_response = camera_handle.ping()
        except Pyro4.errors.CommunicationError as e:
            print e
            return False
        except Pyro4.errors.TimeoutError as e:
            print e
            return False
        if ping_response:
            return True
        else:
            return False

    def identify_leader(self):
        if self.leader_handle:
            response = self.ping_other(self.leader_handle)
            if not response:
                self.determine_leader()
        if not self.leader_handle:
            self.determine_leader()

    # Decide how to do this - I don't want a wait.
    # I think I want to check if the leader pinged back last time I checked - a queue?

    def determine_leader(self):
        for i in range(num_cameras)[:self.cam_id]:
            if i < self.cam_id:
                response = self.ping_other(self.peers[i])
                if response:
                    self.leader_handle = self.peers[i]
                    return True
        self.leader_handle = self.peers[self.cam_id]
        return True
        # Note that this is self.
        # If the camera can't find a lower cam_id, it is the leader.

    def reconcile_kvdb_and_pipeline(self):
        if self.kvdb != self.pipeline.status:
            self.pipeline.change_parameters(self.kvdb)
            # These functions need to be written for the pipeline

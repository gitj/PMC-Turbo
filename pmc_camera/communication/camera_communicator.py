import socket
import time
import Queue
import Pyro4, Pyro4.socketutil, Pyro4.errors
import select
import struct
import threading
import logging

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.COMMTIMEOUT = 1.0
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

base_port = 40000  # Change this const when a base port is decided upon.
num_cameras = 2

port_list = [base_port + i for i in range(num_cameras)]  # Ditto for the IP list and ports.
logger = logging.getLogger(__name__)

START_BYTE = '\x10'
END_BYTE = '\x03'


@Pyro4.expose
class Communicator():
    def __init__(self, cam_id):
        self.port = base_port + cam_id
        logger.debug('Communicator initialized')
        self.cam_id = cam_id
        self.kvdb = dict(value=4.6)
        self.command_dict = {}
        # dict(give_kvdb=self.send_kvdb)
        self.command_queue = Queue.Queue()
        self.leader_handle = None
        self.peers = []
        self.end_loop = False

        self.packet_decoding_methods = {
            '\x13': self.decode_science_request,
            '\x14': self.decode_science_command
        }
        self.science_data_commands = {
            0x00: self.request_autoexposure,
            0x01: self.request_autofocus,
            0x02: self.request_postage_stamp,
            0x03: self.send_overall_status,
            0x04: self.send_specific_status,
            0x05: self.run_python_command,
            0x06: self.run_linux_command,
            0x07: self.change_to_preset_acquistion_mode
        }
        self.pyro_daemon = None
        self.sip_uplink_socket = None
        self.sip_downlink_socket = None
        self.sip_downlink_ip, self.sip_downlink_port = None, None
        self.pyro_thread = None
        self.leader_thread = None
        self.buffer_for_downlink = ''
        # We will instantiate these later

        self.ip_list = None
        self.port_list = None

        self.setup_pyro()
        self.start_pyro_thread()
        self.get_communicator_handles(self.ip_list, self.port_list)

    def __del__(self):
        if self.pyro_thread and self.pyro_thread.is_alive():
            self.pyro_thread.join(timeout=0)
        if self.leader_thread and self.leader_thread.is_alive():
            self.leader_thread.join(timeout=0)
        if self.pyro_daemon:
            self.pyro_daemon.shutdown()
        if self.sip_uplink_socket:
            self.sip_uplink_socket.close()
        if self.sip_downlink_socket:
            self.sip_downlink_socket.close()
        logger.debug('Communicator deleted')

    def setup_pyro(self):
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')

        self.ip_list = [ip] * num_cameras
        self.port_list = [base_port + i for i in range(num_cameras)]

        self.pyro_daemon = Pyro4.Daemon(host=ip, port=self.port)
        uri = self.pyro_daemon.register(self, "communicator")
        print uri

    def setup_leader_attributes(self, sip_uplink_ip, sip_uplink_port, sip_downlink_ip, sip_downlink_port):
        self.sip_buffer = ''
        self.leftover_buffer = ''
        self.setup_sip_uplink_socket(sip_uplink_ip, sip_uplink_port)
        self.setup_sip_downlink_socket(sip_downlink_ip, sip_downlink_port)
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
        # self.run_pyro_tasks()
        self.reconcile_kvdb_and_pipeline()

    def start_leader_thread(self):
        self.leader_thread = threading.Thread(target=self.leader_loop)
        self.leader_thread.daemon = True
        self.leader_thread.start()

    def leader_loop(self):
        while True:
            self.run_leader_tasks()
            if self.end_loop == True:
                # Switch this to end the pyro loop.
                return
            # time.sleep(0.01)
            time.sleep(1)

    def run_leader_tasks(self):
        self.get_bytes_from_sip_socket()
        self.get_packets_from_buffer()
        # elf.run_pyro_tasks()
        # self.process_sip_socket()
        # self.process_packet_queue()

    def start_pyro_thread(self):
        self.pyro_thread = threading.Thread(target=self.pyro_loop)
        self.pyro_thread.daemon = True
        self.pyro_thread.start()

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
        events, _, _ = select.select(self.pyro_daemon.sockets, [], [], 0)
        if events:
            self.pyro_daemon.events(events)
            # else:
            #    time.sleep(0.001)

    ### leader methods

    def respond_to_science_data_request(self):
        logger.debug("Science data request received.")
        msg = self.package_updates_for_downlink()
        self.send_message_to_downlink(msg)
        return
        # return self.send_overall_status()

    def respond_to_science_command(self, msg):
        self.buffer_for_downlink += msg
        #   # Just echo the message back into the buffer right now
        format_string = '<4B%ds' % (len(msg) - 4)
        sequence, verify, which, command, args = struct.unpack(format_string, msg)
        self.science_data_commands[command](which, sequence, verify, args)

    def package_updates_for_downlink(self):
        # Constantly keep a buffer of stuff I want to send on downlink.
        # When this function is called, package that stuff as a 255 byte package to be sent on downlink
        # Then clear the buffer.
        buffer = self.buffer_for_downlink
        self.buffer_for_downlink = ''
        return buffer

    def process_gps_position(self, gps_position_dict):
        return

    def process_gps_time(self, gps_time_dict):
        return

    def process_mks_pressure_altitude(self, mks_pressure_altitude_dict):
        return

    def request_autoexposure(self, which, sequence, verify, args):
        format_string = '<3B%ds' % (len(args) - 3)
        start, stop, step, padding = struct.unpack(format_string, args)
        if True:
            print 'Autofocus command received'
            print 'which: %d, sequence: %d, verify: %d' % (which, sequence, verify)
            print 'start: %d, stop: %d, step: %d' % (start, stop, step)
            # return self.peers[which].run_autoexposure(start, stop, step)

    def request_autofocus(self, which, sequence, verify, args):
        format_string = '<3B%ds' % (len(args) - 3)
        start, stop, step, padding = struct.unpack(format_string, args)
        if True:
            print 'Autofocus command received'
            print 'which: %d, sequence: %d, verify: %d' % (which, sequence, verify)
            print 'start: %d, stop: %d, step: %d' % (start, stop, step)
            # return self.peers[which].run_autofocus(start, stop, step)

    def request_postage_stamp(self, which, sequence, verify, args):
        compression_factor = args[0]
        return self.peers[which].get_postage_stamp(compression_factor)

    def send_overall_status(self, which=None, sequence=None, verify=None, args=None):
        # Need to decide what to do heres
        # Send 1 for everything that's okay, 0 for everything that isn't
        status_summaries = []
        for peer in self.peers:
            status_summaries.append(peer.give_status_summary())
        return status_summaries

    def send_specific_status(self, which, sequence, verify, args):
        return self.peers[which].get_detailed_status()

    def run_python_command(self, which, sequence, verify, args):
        return

    def run_linux_command(self, which, sequence, verify, args):
        return

    def change_to_preset_acquistion_mode(self, which, sequence, verify, args):
        return

    ##### SIP socket methods

    def setup_sip_uplink_socket(self, sip_uplink_ip, sip_uplink_port):
        # sip_ip='192.168.1.137', sip_port=4001 in our experimental setup.
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_.bind((sip_uplink_ip, sip_uplink_port))
        # socket_.settimeout(0)
        self.sip_uplink_socket = socket_

    def setup_sip_downlink_socket(self, sip_downlink_ip, sip_downlink_port):
        # sip_downlink_ip='192.168.1.253', sip_downlink_port=4001 in our experimental setup.
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip_downlink_ip, self.sip_downlink_port = sip_downlink_ip, sip_downlink_port
        self.sip_downlink_socket = socket_

    def send_message_to_downlink(self, data):
        HEADER = '\x10\x53'
        FOOTER = '\x03'
        format_string = '1B%ds' % len(data)
        msg = struct.pack(format_string, len(data), data)
        msg = HEADER + msg + FOOTER
        # print msg
        self.sip_downlink_socket.sendto(msg, (self.sip_downlink_ip, self.sip_downlink_port))

    def get_bytes_from_sip_socket(self):
        self.sip_uplink_socket.settimeout(0)
        # Note sure why this throws an error, but we already set timeout to 0.
        done = False
        while True:
            try:
                data = self.sip_uplink_socket.recv(1024)
                logger.debug('%r' % data)
                self.sip_buffer = self.sip_buffer + data
            except:
                # This should except a timeouterrror.
                return

    def get_packets_from_buffer(self):
        while self.sip_buffer != '':
            idx = self.sip_buffer.find(START_BYTE)
            if idx == -1:
                # This means the START_BYTE was not found
                # We just want to discard the buffer.
                return
            id_byte = self.sip_buffer[idx + 1]
            if not id_byte in self.packet_decoding_methods:
                # If the id_byte is not valid, we cut off the junk and continue the loop.
                self.sip_buffer = self.sip_buffer[idx + 2:]
                continue
            if id_byte in self.packet_decoding_methods.keys():
                # Decoding method handles unfinished packets.
                # It returns how long the message it interpreted was.
                message_length = self.packet_decoding_methods[id_byte](self.sip_buffer[idx:])
                self.sip_buffer = self.sip_buffer[idx + message_length:]

    def decode_science_request(self, buffer):
        if buffer[2] == END_BYTE:
            self.respond_to_science_data_request()
            return 3
        else:
            # Put the hanging bytes into the sip_buffer
            self.sip_buffer += buffer
            # This better be 2...
            # This cause the buffer to go to the end.
            return len(buffer)

    def decode_science_command(self, buffer):
        logger.debug('logging science command')
        length, = struct.unpack('<1B', buffer[2])
        if buffer[3 + length] == END_BYTE:
            format_string = '<%ds' % length
            logger.debug('%r' % buffer)
            msg, = struct.unpack(format_string, buffer[3:3+length])
            self.respond_to_science_command(msg)
            return len(buffer[:(3+length)])
        else:
            self.leftover_buffer += buffer
            return len(buffer)

    ### peer methods

    def ping(self):
        return True

    def ping_other(self, camera_handle):
        # Need to add timeout to this, as well as a case for no ping.
        try:
            return camera_handle.ping()
        except (Pyro4.errors.CommunicationError, Pyro4.errors.TimeoutError) as e:
            print e
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

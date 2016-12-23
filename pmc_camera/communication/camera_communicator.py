from __future__ import division
import socket
import time
import Queue
import Pyro4, Pyro4.socketutil, Pyro4.errors
import select
import struct
import threading
import logging
import sip_buffer_receiving_methods
import numpy as np
from pmc_camera.communication import downlink_classes, uplink_classes

from pmc_camera.communication import constants

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]
Pyro4.config.COMMTIMEOUT = 1.0
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

base_port = 40000  # Change this const when a base port is decided upon.
num_cameras = 2

port_list = [base_port + i for i in range(num_cameras)]  # Ditto for the IP list and ports.
logger = logging.getLogger(__name__)

START_BYTE = chr(constants.SIP_START_BYTE)
END_BYTE = chr(constants.SIP_END_BYTE)


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
        self.end_loop = True
        time.sleep(0.01)
        if self.pyro_thread and self.pyro_thread.is_alive():
            self.pyro_thread.join(timeout=0)
        if self.leader_thread and self.leader_thread.is_alive():
            self.leader_thread.join(timeout=0)
        if self.pyro_daemon:
            self.pyro_daemon.shutdown()
        logger.debug('Communicator deleted')

    def setup_pyro(self):
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')

        self.ip_list = [ip] * num_cameras
        self.port_list = [base_port + i for i in range(num_cameras)]

        self.pyro_daemon = Pyro4.Daemon(host=ip, port=self.port)
        uri = self.pyro_daemon.register(self, "communicator")
        print uri

    def setup_leader_attributes(self, sip_uplink_ip, sip_uplink_port, lowrate_downlink_ip, lowrate_downlink_port,
                                hirate_downlink_ip, hirate_downlink_port, downlink_speed):
        self.sip_leftover_buffer = ''
        self.leftover_buffer = ''
        self.lowrate_uplink = uplink_classes.LowrateUplink(sip_uplink_ip, sip_uplink_port)
        self.lowrate_downlink = downlink_classes.LowrateDownlink(lowrate_downlink_ip, lowrate_downlink_port)
        self.hirate_downlink = downlink_classes.HirateDownlink(hirate_downlink_ip, hirate_downlink_port, downlink_speed)
        self.downlinks = [self.hirate_downlink]
        self.file_id = 12

        self.image_server = Pyro4.Proxy('PYRO:image@192.168.1.30:50001')

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
        logger.debug('Starting leader thread')
        self.leader_thread.start()

    def leader_loop(self):
        while True:
            self.get_housekeeping()
            self.get_and_process_sip_bytes()
            # self.try_to_send_image()
            self.send_data_on_downlinks()
            if self.end_loop == True:
                # Switch this to end the leader loop.
                return
            time.sleep(1)

    def get_housekeeping(self):
        # Eventually this should query all the subsystems and condense to a housekeeping report.
        # For now we will keep it simple - just returns a 1 for each of the cameras.
        fileinfo = self.image_server.get_latest_fileinfo()
        frame_status = fileinfo[3]
        frame_id = fileinfo[4]
        focus_step = fileinfo[7]
        aperture_stop = fileinfo[8]
        exposure_ms = int(fileinfo[9] / 1000)
        self.buffer_for_downlink += struct.pack('>1B1L1L1H1H1L', 255, frame_status, frame_id,
                                                focus_step, aperture_stop, exposure_ms)

    def send_data_on_downlinks(self):
        for link in self.downlinks:
            if link.has_bandwidth():
                next_data = self.peers[0].get_next_data()
                #next_data = self.get_next_data()

                self.file_id += 1
                # This will be replaced by (communicators[next_communicator].get_next_data() eventually.
                link.put_data_into_queue(next_data, self.file_id, file_type=1)
            else:
                link.send_data()

    def get_next_data(self):
        # buffer = hirate_sending_methods.get_buffer_from_file('cloud_icon.jpg')
        buffer, fileinfo = self.image_server.get_latest_jpeg()
        frame_status = fileinfo[3]
        frame_id = fileinfo[4]
        focus_step = fileinfo[7]
        aperture_stop = fileinfo[8]
        exposure_ms = int(fileinfo[9] / 1000)
        buffer = struct.pack('>1L1L1H1H1L', frame_status, frame_id, focus_step, aperture_stop,
                             exposure_ms) + buffer
        return buffer

    def start_pyro_thread(self):
        self.pyro_thread = threading.Thread(target=self.pyro_loop)
        self.pyro_thread.daemon = True
        logger.debug('Stating pyro thread')
        self.pyro_thread.start()

    def pyro_loop(self):
        while True:
            events, _, _ = select.select(self.pyro_daemon.sockets, [], [], 0)
            # Check this carefully for bugs - I think I eliminated them but make sure.
            if events:
                self.pyro_daemon.events(events)
            if self.end_loop == True:
                # Switch this to end the pyro loop.
                return
            time.sleep(0.01)

    ### leader methods

    def respond_to_science_data_request(self):
        logger.debug("Science data request received.")
        msg = self.package_updates_for_downlink()
        self.lowrate_downlink.send(msg)
        return
        # return self.send_overall_status()

    def respond_to_science_command(self, msg):
        logger.debug('%r' % msg)
        self.buffer_for_downlink += msg
        #   # Just echo the message back into the buffer right now
        format_string = '<5B%ds' % (len(msg) - 5)
        length, sequence, verify, which, command, args = struct.unpack(format_string, msg)
        logger.debug('sequence: %d verify: %d which: %d command: %d' % (sequence, verify, which, command))
        self.science_data_commands[command](which, sequence, verify, args)

    def package_updates_for_downlink(self):
        # Constantly keep a buffer of stuff I want to send on downlink.
        # When this function is called, package that stuff as a 255 byte package to be sent on downlink
        # Then clear the buffer.
        buffer = self.buffer_for_downlink
        logger.debug('Packaging buffer for downlink: %r' % buffer)
        if len(buffer) > 255:
            logger.error('Buffer length %d. Buffer: %r' % (len(buffer), buffer))
            buffer = buffer[:256]
        if len(buffer) == 0:
            logger.warning('Empty buffer')
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
            logger.debug('Autofocus command received')
            logger.debug('which: %d, sequence: %d, verify: %d' % (which, sequence, verify))
            logger.debug('start: %d, stop: %d, step: %d' % (start, stop, step))
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

    def get_and_process_sip_bytes(self):
        valid_packets = self.lowrate_uplink.get_sip_bytes()
        if valid_packets:
            for packet in valid_packets:
                print '%r' % packet
                self.execute_packet(packet)

    def execute_packet(self, packet):
        id_byte = packet[1]
        logger.debug('Got packet with id %r' % id_byte)
        if id_byte == '\x13':
            self.respond_to_science_data_request()
        if id_byte == '\x14':
            self.respond_to_science_command(packet[2:-1])  ### peer methods

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

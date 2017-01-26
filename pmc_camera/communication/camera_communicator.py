from __future__ import division
import time
import traceback

import Pyro4, Pyro4.socketutil, Pyro4.errors, Pyro4.util
import select
import struct
import threading
import logging

import pmc_camera.communication.command_classes
import pmc_camera.communication.packet_classes
from pmc_camera.communication import downlink_classes, uplink_classes  # aggregator
from pmc_camera.communication.command_table import command_manager, CommandStatus
from pmc_camera.communication import command_table
from pmc_camera.communication import housekeeping_format_classes

from pmc_camera.communication import constants
from pmc_camera.communication import aggregator_hard_coded

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]
Pyro4.config.COMMTIMEOUT = 1.0
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

BASE_PORT = 40000  # Change this const when a base port is decided upon.
num_cameras = 2

port_list = [BASE_PORT + i for i in range(num_cameras)]  # Ditto for the IP list and ports.
logger = logging.getLogger(__name__)

START_BYTE = chr(constants.SIP_START_BYTE)
END_BYTE = chr(constants.SIP_END_BYTE)




@Pyro4.expose
class Communicator():
    def __init__(self, cam_id, peers, controller, base_port=BASE_PORT, start_pyro=True):
        self.port = base_port + cam_id
        logger.debug('Communicator initialized')
        self.cam_id = cam_id
        self.peers = peers
        self.controller = controller
        self.aggregator = None
        self.peer_polling_order_idx = 0
        self.peer_polling_order = [0]
        self.end_loop = False

        self.pyro_daemon = None
        self.pyro_thread = None
        self.leader_thread = None
        self.lowrate_uplink = None
        self.buffer_for_downlink = struct.pack('>255B', *([0] * 255))

        self.command_logger = pmc_camera.communication.command_classes.CommandLogger()

        # TODO: Set up proper destination lists, including LIDAR, narrow field, wide field, and all
        self.destination_lists = dict(enumerate([[peer] for peer in peers]))
        self.destination_lists[command_table.DESTINATION_ALL_CAMERAS] = peers

        # We will instantiate these later
        if start_pyro:
            self.setup_pyro()
            self.start_pyro_thread()

    def validate_command_table(self):
        """
        Ensure that all available commands defined in command_table are actually implemented by the communicator

        Raises
        -------
        AttributeError if a command in the table is not implemented
        """
        for command in command_manager.commands:
            try:
                function = getattr(self, command.name)
            except AttributeError:
                raise AttributeError("Command %s is not implemented by communicator!" % command.name)

    def close(self):
        self.end_loop = True
        time.sleep(0.01)
        if self.pyro_thread and self.pyro_thread.is_alive():
            self.pyro_thread.join(timeout=0)
        if self.leader_thread and self.leader_thread.is_alive():
            self.leader_thread.join(timeout=0)
        try:
            self.pyro_daemon.shutdown()
        except Exception:
            pass
        try:
            self.lowrate_uplink.uplink_socket.close()
        except Exception:
            pass
        logger.debug('Communicator deleted')

    def setup_pyro(self):
        self.pyro_daemon = Pyro4.Daemon(host='0.0.0.0', port=self.port)
        uri = self.pyro_daemon.register(self, "communicator")
        print uri

    def setup_leader_attributes(self, sip_uplink_port, lowrate_downlink_ip, lowrate_downlink_port, hirate_downlink_ip,
                                hirate_downlink_port, downlink_speed):
        self.sip_leftover_buffer = ''
        self.leftover_buffer = ''
        self.lowrate_uplink = uplink_classes.LowrateUplink(sip_uplink_port)
        self.lowrate_downlink = downlink_classes.LowrateDownlink(lowrate_downlink_ip, lowrate_downlink_port)
        self.hirate_downlink = downlink_classes.HirateDownlink(hirate_downlink_ip, hirate_downlink_port, downlink_speed)
        self.downlinks = [self.hirate_downlink]  # Eventually this will also include Openport downlink
        self.file_id = 254
        # self.peer_aggregator = aggregator.PeerAggregator()

    ### Loops to continually be run

    def start_leader_thread(self):
        self.leader_thread = threading.Thread(target=self.leader_loop)
        self.leader_thread.daemon = True
        logger.debug('Starting leader thread')
        self.leader_thread.start()

    def leader_loop(self):
        while True:

            self.get_and_process_sip_bytes()
            self.send_data_on_downlinks()
            if self.end_loop == True:  # Switch this to end the leader loop.
                return
            time.sleep(1)

    def old_get_housekeeping(self):
        # Eventually this should query all the subsystems and condense to a housekeeping report.
        # For now I will add some filler data.
        fileinfo = self.controller.get_latest_fileinfo()
        frame_status = fileinfo[3]
        frame_id = fileinfo[4]
        focus_step = fileinfo[7]
        aperture_stop = fileinfo[8]
        exposure_ms = int(fileinfo[9] / 1000)
        camera0_status = struct.pack('>1B1L1L1H1H1L', 255, frame_status, frame_id,
                                     focus_step, aperture_stop, exposure_ms)
        self.buffer_for_downlink = camera0_status + self.buffer_for_downlink[
                                                    struct.calcsize('>1B1L1L1H1H1L'):]  # just overwrite old status
        # self.buffer_for_downlink = self.peer_aggregator.aggregate_peer_status(self.peers)

    def get_housekeeping(self):
        if self.aggregator == None:
            raise RuntimeError('Communicator has no aggregator.')
        self.aggregator.update()
        status_summary = self.aggregator.get_status_summary()
        short_housekeeping = housekeeping_format_classes.ShortHousekeeping()
        short_housekeeping.from_values([self.cam_id], [status_summary])
        camera_status = short_housekeeping.to_buffer()
        self.buffer_for_downlink = camera_status + self.buffer_for_downlink[len(camera_status):]

    def setup_aggregator(self, aggregator):
        self.aggregator = aggregator

    def send_detailed_housekeeping(self):
        self.aggregator.update()
        json_file = self.aggregator.to_json_file()
        self.downlinks[0].put_data_into_queue(json_file.to_buffer(), self.file_id)
        self.file_id += 1

    def send_data_on_downlinks(self):
        if not self.peers:
            raise RuntimeError(
                'Communicator has no peers. This should never happen; leader at minimum has self as peer.')
        for link in self.downlinks:
            if link.has_bandwidth():
                logger.debug('Getting next data from camera %d' % self.peer_polling_order[self.peer_polling_order_idx])
                next_data = self.peers[self.peer_polling_order[self.peer_polling_order_idx]].get_next_data()
                self.peer_polling_order_idx = (self.peer_polling_order_idx + 1) % len(self.peer_polling_order)
                link.put_data_into_queue(next_data, self.file_id)
                self.file_id += 1
            else:
                link.send_data()

    def get_next_data(self):
        try:
            return self.controller.get_next_data_for_downlink()
        except Exception:
            raise Exception("".join(Pyro4.util.getPyroTraceback()))

    def start_pyro_thread(self):
        self.pyro_thread = threading.Thread(target=self.pyro_loop)
        self.pyro_thread.daemon = True
        logger.debug('Stating pyro thread')
        self.pyro_thread.start()

    def pyro_loop(self):
        while True:
            events, _, _ = select.select(self.pyro_daemon.sockets, [], [], 0.01)
            if events:
                self.pyro_daemon.events(events)
            if self.end_loop == True:
                return

    ### The following two functions respond to SIP requests
    def respond_to_science_data_request(self):
        logger.debug("Science data request received.")
        self.get_housekeeping()
        self.lowrate_downlink.send(self.buffer_for_downlink)

    def process_science_command_packet(self, msg):
        try:
            command_packet = pmc_camera.communication.packet_classes.CommandPacket(buffer=msg)
        except (pmc_camera.communication.packet_classes.PacketError, ValueError) as e:
            logger.exception("Failed to decode command packet")
            return
        destinations = self.destination_lists[command_packet.destination]
        for number, destination in enumerate(destinations):
            try:
                logger.debug("pinging destination %d member %d" % (command_packet.destination, number))
                destination.ping()
            except Exception as e:
                details = "Ping failure for destination %d, member %d\n" % (command_packet.destination, number)
                details += traceback.format_exc()
                pyro_details = ''.join(Pyro4.util.getPyroTraceback())
                details = details + pyro_details
                self.command_logger.add_command_result(command_packet.sequence_number,
                                                       CommandStatus.failed_to_ping_destination,
                                                       details)
                logger.warning(details)
                return

        command_name = "None"
        number = 0
        kwargs = {}
        try:
            commands = command_manager.decode_commands(command_packet.payload)
            for number, destination in enumerate(destinations):
                for command_name, kwargs in commands:
                    logger.debug("Executing command %s at destination %d member %d with kwargs %r" % (command_name,
                                                                                                      command_packet.destination,
                                                                                                      number, kwargs))
                    function = getattr(destination, command_name)
                    function(**kwargs)
        except Exception as e:
            details = ("Failure while executing command %s at destination %d member %d with arguments %r\n"
                       % (command_name, command_packet.destination, number, kwargs))
            details += traceback.format_exc()
            pyro_details = ''.join(Pyro4.util.getPyroTraceback())
            details = details + pyro_details
            self.command_logger.add_command_result(command_packet.sequence_number, CommandStatus.command_error, details)
            logger.warning(details)
            return
        self.command_logger.add_command_result(command_packet.sequence_number, CommandStatus.command_ok, '')

    def set_peer_polling_order(self, new_peer_polling_order):
        self.peer_polling_order = new_peer_polling_order
        self.peer_polling_order_idx = 0

    def set_focus(self, focus_step):
        self.controller.set_focus(focus_step)

    def set_exposure(self, exposure_time_us):
        self.controller.set_exposure(exposure_time_us)

    def request_specific_file(self, filename, max_num_bytes, request_id):
        self.controller.request_specific_file(filename, max_num_bytes, request_id)

    def run_shell_command(self, command_line, max_num_bytes_returned, request_id, timeout):
        self.controller.run_shell_command(command_line, max_num_bytes_returned, request_id, timeout)

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

    ##### SIP socket methods

    def get_and_process_sip_bytes(self):
        valid_packets = self.lowrate_uplink.get_sip_packets()
        if valid_packets:
            for packet in valid_packets:
                print '%r' % packet
                self.execute_packet(packet)

    def execute_packet(self, packet):
        # Improve readability here - constants in uplink classes
        id_byte = packet[1]
        logger.debug('Got packet with id %r' % id_byte)
        if id_byte == chr(constants.SCIENCE_DATA_REQUEST_BYTE):
            self.respond_to_science_data_request()
        if id_byte == chr(constants.SCIENCE_COMMAND_BYTE):
            self.process_science_command_packet(packet)  ### peer methods

    def ping(self):
        return True

    def ping_other(self, camera_handle):
        # Need to add timeout to this, as well as a case for no ping.
        try:
            return camera_handle.ping()
        except (Pyro4.errors.CommunicationError, Pyro4.errors.TimeoutError) as e:
            print e
            return False

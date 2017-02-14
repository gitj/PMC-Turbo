from __future__ import division

import json
import logging
import select
import struct
import threading
import time
import traceback

import Pyro4
import Pyro4.errors
import Pyro4.socketutil
import Pyro4.util

from pmc_turbo.communication import command_table, command_classes
from pmc_turbo.communication import constants
from pmc_turbo.communication import downlink_classes, uplink_classes, packet_classes
from pmc_turbo.communication import file_format_classes
from pmc_turbo.communication.command_table import command_manager, CommandStatus
from pmc_turbo.utils import error_counter, camera_id

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]
Pyro4.config.COMMTIMEOUT = 1.0
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

BASE_PORT = 40000  # Change this const when a base port is decided upon.

logger = logging.getLogger(__name__)

START_BYTE = chr(constants.SIP_START_BYTE)
END_BYTE = chr(constants.SIP_END_BYTE)


@Pyro4.expose
class Communicator():
    def __init__(self, cam_id, peers, controller, base_port=BASE_PORT, start_pyro=True, loop_interval=1):
        self.port = base_port + cam_id
        logger.debug('Communicator initialized')
        self.cam_id = cam_id

        self.peers = []
        for peer in peers:
            try:
                self.peers.append(Pyro4.Proxy(peer))
            except TypeError as e:
                if not hasattr(peer, '_pyroUri'):
                    if not hasattr(peer, 'cam_id'):
                        raise e
                else:
                    self.peers.append(peer)

        if controller:
            try:
                self.controller = Pyro4.Proxy(controller)
            except TypeError as e:
                if hasattr(controller, '_pyroUri') or hasattr(controller, 'pipeline'):
                    self.controller = controller
                else:
                    raise Exception("Invalid controller argument; must be URI string, URI object, or controller class")

        self.peer_polling_order_idx = 0
        self.peer_polling_order = [0]
        self.synchronize_image_time_across_cameras = False
        self.end_loop = False
        self.status_groups = []
        self.loop_interval = loop_interval

        peer_error_strings = [('pmc_%d_communication_error_counts' % i) for i in range(len(self.peers))]
        self.error_counter = error_counter.CounterCollection('communication_errors', '/tmp/logs/',
                                                             'controller_communication_error_counts',
                                                             *peer_error_strings)

        self.pyro_daemon = None
        self.pyro_thread = None
        self.leader_thread = None
        self.lowrate_uplink = None
        self.buffer_for_downlink = struct.pack('>255B', *([0] * 255))

        self.command_logger = command_classes.CommandLogger()

        # TODO: Set up proper destination lists, including LIDAR, narrow field, wide field, and all
        self.destination_lists = dict(enumerate([[peer] for peer in self.peers]))
        self.destination_lists[command_table.DESTINATION_ALL_CAMERAS] = self.peers

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

    def setup_links(self, sip_uplink_port, lowrate_downlink_ip, lowrate_downlink_port, hirate_downlink_ip,
                    hirate_downlink_port, downlink_speed):
        self.sip_leftover_buffer = ''
        self.leftover_buffer = ''
        self.lowrate_uplink = uplink_classes.LowrateUplink(sip_uplink_port)
        self.lowrate_downlink = downlink_classes.LowrateDownlink(lowrate_downlink_ip, lowrate_downlink_port)
        self.hirate_downlink = downlink_classes.HirateDownlink(hirate_downlink_ip, hirate_downlink_port, downlink_speed)
        self.downlinks = [self.hirate_downlink]  # Eventually this will also include Openport downlink
        self.file_id = 0

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
            time.sleep(self.loop_interval)

    def add_status_group(self, status_group):
        self.status_groups.append(status_group)

    def send_data_on_downlinks(self):
        if not self.peers:
            raise RuntimeError(
                'Communicator has no peers. This should never happen; leader at minimum has self as peer.')
        for link in self.downlinks:
            if link.has_bandwidth():
                if self.synchronize_image_time_across_cameras and self.peer_polling_order_idx == 0:
                    self.request_synchronized_images()
                logger.debug('Getting next data from camera %d' % self.peer_polling_order[self.peer_polling_order_idx])
                next_data = None
                active_peer = self.peers[self.peer_polling_order[self.peer_polling_order_idx]]
                try:
                    next_data = active_peer.get_next_data()

                except Pyro4.errors.CommunicationError as e:
                    active_peer_string = str(active_peer._pyroUri)
                    error_counter_key = 'pmc_%d_communication_error_counts' % self.peer_polling_order[
                        self.peer_polling_order_idx]
                    self.error_counter.counters[error_counter_key].increment()
                    logger.debug('Connection to peer at URI %s failed. Error counter - %r. Error message: %s' % (
                        active_peer_string, self.error_counter.counters[error_counter_key], str(e)))

                if not next_data:
                    logger.debug('No data was obtained.')
                else:
                    link.put_data_into_queue(next_data, self.file_id)
                    self.file_id += 1

                self.peer_polling_order_idx = (self.peer_polling_order_idx + 1) % len(self.peer_polling_order)

            else:
                link.send_data()

    def request_synchronized_images(self):
        timestamp = time.time()-2 # TODO: this should probably be a parameter in settings file
        for peer in self.peers:
            logger.debug("Synchronizing images by requesting standard image closest to timestamp %f from peer %r" %
                         (timestamp,peer))
            peer.request_standard_image_at(timestamp)

    def request_standard_image_at(self,timestamp):
        try:
            self.controller.request_standard_image_at(timestamp)
        except Pyro4.errors.CommunicationError:
            self.error_counter.controller.increment()
            logger.debug('Connection to controller failed. Error counter - %r. Error message: %s' % (
                    self.error_counter.controller, "".join(Pyro4.util.getPyroTraceback())))
        except Exception:
            raise Exception("".join(Pyro4.util.getPyroTraceback()))


    def get_next_data(self):
        try:
            return self.controller.get_next_data_for_downlink()
        except Pyro4.errors.CommunicationError:
            self.error_counter.controller.increment()
            logger.debug(
                'Connection to controller failed. Error counter - %r. Error message: %s' % (
                    self.error_counter.controller, "".join(Pyro4.util.getPyroTraceback())))
            return None
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
        self.get_status_summary()
        self.lowrate_downlink.send(self.buffer_for_downlink)

    def process_science_command_packet(self, msg):
        try:
            command_packet = packet_classes.CommandPacket(buffer=msg)
        except (packet_classes.PacketError, ValueError) as e:
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

        command_name = "<Unknown>"
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

    def get_status_summary(self):
        if len(self.status_groups) == 0:
            raise RuntimeError('Communicator has no status_groups.')
        summary = []
        for group in self.status_groups:
            group.update()
            summary.append(group.get_status())
        camera_status = self.summarize_status_to_255_bytes(summary)
        self.buffer_for_downlink = camera_status + self.buffer_for_downlink[len(camera_status):]

    def summarize_status_to_255_bytes(self, summary):
        # This stub function needs to be filled out.
        return '\xff' * 255

    ##################################################################################################
    # The following methods correspond to commands defined in pmc_turbo.communication.command_table

    def get_status_report(self,compress,request_id):
        logger.debug('Status report requested')
        summary = []
        for group in self.status_groups:
            group.update()
            summary.append(group.get_status())
        payload = json.dumps(summary)
        if compress:
            file_class = file_format_classes.CompressedJSONFile
        else:
            file_class = file_format_classes.JSONFile
        json_file = file_class(payload=payload, filename=(
            'status_summary_%s.json' % time.strftime('%Y-%M-%d-%H:%M:%s')), timestamp=time.time(),
                                                           camera_id=camera_id.get_camera_id(),
                                                           request_id=request_id)

        self.controller.add_file_to_downlink_queue(json_file.to_buffer())

    def set_peer_polling_order(self, new_peer_polling_order):
        self.peer_polling_order = new_peer_polling_order
        self.peer_polling_order_idx = 0

    def set_focus(self, focus_step):
        self.controller.set_focus(focus_step)

    def set_exposure(self, exposure_time_us):
        self.controller.set_exposure(exposure_time_us)

    def set_standard_image_parameters(self, row_offset, column_offset, num_rows, num_columns, scale_by, quality):
        self.controller.set_standard_image_paramters(row_offset=row_offset, column_offset=column_offset,
                                                     num_rows=num_rows,
                                                     num_columns=num_columns, scale_by=scale_by, quality=quality)

    def request_specific_images(self, timestamp, request_id, row_offset, column_offset, num_rows, num_columns,
                                scale_by, quality, step):
        self.controller.request_specific_images(timestamp=timestamp, request_id=request_id, row_offset=row_offset,
                                                column_offset=column_offset, num_rows=num_rows, num_columns=num_columns,
                                                scale_by=scale_by, quality=quality, step=step)

    def request_specific_file(self, filename, max_num_bytes, request_id):
        self.controller.request_specific_file(filename, max_num_bytes, request_id)

    def run_shell_command(self, command_line, max_num_bytes_returned, request_id, timeout):
        self.controller.run_shell_command(command_line, max_num_bytes_returned, request_id, timeout)

    def flush_downlink_queues(self):
        self.controller.flush_downlink_queue()
        for link in self.downlinks:
            link.flush_packet_queue()

    def use_synchronized_images(self,synchronize):
        self.synchronize_image_time_across_cameras = bool(synchronize)


    # end command table methods
    ###################################################################################################################

    ##### SIP socket methods

    def get_and_process_sip_bytes(self):
        valid_packets = self.lowrate_uplink.get_sip_packets()
        if valid_packets:
            for packet in valid_packets:
                logger.debug('Found packet: %r' % packet)
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

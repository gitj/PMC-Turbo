from __future__ import division

import json
import logging
import select
import struct
import threading
import time
import traceback
from pymodbus.exceptions import ConnectionException
from pmc_turbo.utils.configuration import GlobalConfiguration
from traitlets import Int, Unicode, Bool, List, Float, Tuple, Bytes, TCPAddress, Dict, Enum

import Pyro4
import Pyro4.errors
import Pyro4.socketutil
import Pyro4.util

from pmc_turbo.communication import command_table, command_classes
from pmc_turbo.communication import constants
from pmc_turbo.communication import downlink_classes, uplink_classes, packet_classes
from pmc_turbo.communication import file_format_classes
from pmc_turbo.communication.command_table import command_manager, CommandStatus
from pmc_turbo.communication.short_status import ShortStatusLeader, ShortStatusCamera
from pmc_turbo.housekeeping.charge_controller import ChargeControllerLogger
from pmc_turbo.communication import keyring

from pmc_turbo.utils import error_counter, camera_id

Pyro4.config.SERVERTYPE = "multiplex"
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]
# Caution: If COMMTIMEOUT is too low, camera communicator gets a timeout error when it requests data from another communicator.
Pyro4.config.COMMTIMEOUT = 5
# Tests show COMMTIMEOUT works.
# Note that there is another timeout POLLTIMEOUT
# "For the multiplexing server only: the timeout of the select or poll calls"

logger = logging.getLogger(__name__)

START_BYTE = chr(constants.SIP_START_BYTE)
END_BYTE = chr(constants.SIP_END_BYTE)


@Pyro4.expose
class Communicator(GlobalConfiguration):
    initial_peer_polling_order = List(trait=Int).tag(config=True)
    loop_interval = Float(default_value=0.01, allow_none=False, min=0).tag(config=True)
    lowrate_link_parameters = List(
        trait=Tuple(Enum(("comm1", "comm2")), TCPAddress(), Int(default_value=5001, min=1024, max=65535)),
        help='List of tuples - link name, lowrate downlink address and lowrate uplink port.'
             'e.g. [(("pmc-serial-1", 5001), 5001), ...]').tag(config=True)
    hirate_link_parameters = List(trait=Tuple(Enum(("openport", "highrate", "los")), TCPAddress(), Int(min=0)),
                                  help='List of tuples - hirate downlink name, Enum(("openport", "highrate", "los"))'
                                       'hirate downlink address,'
                                       'hirate downlink downlink speed in bytes per second. 0 means link is disabled.'
                                       'e.g. [("openport", ("192.168.1.70", 4501), 10000), ...]').tag(config=True)
    use_controller = Bool(default_value=True).tag(config=True)
    synchronized_image_delay = Float(2.0, min=0,
                                     help="Number of seconds in the past to request images from all cameras "
                                          "when synchronized image mode is enabled. This value should be set "
                                          "large enough to ensure that all cameras have an image ready.").tag(
        config=True)
    charge_controller_settings = List(trait=Tuple(TCPAddress(), Float(10, min=0), Float(3600, min=0)),
                                      help="List of tuples ((ip,port), measurement_interval, eeprom_measurement_interval)\n").tag(
        config=True)

    def __init__(self, cam_id, peers, controller, leader, pyro_port, **kwargs):
        super(Communicator, self).__init__(**kwargs)
        self.port = pyro_port
        logger.debug('Communicator initialized')
        self.cam_id = cam_id
        self.leader_id = 0 # this will be deprecated when the full election is in place.
        self.become_leader = False

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
        else:
            if self.use_controller:
                controller_uri = 'PYRO:controller@%s:%d' % ('0.0.0.0', self.controller_pyro_port)
                self.controller = Pyro4.Proxy(controller_uri)

        self.peer_polling_order_idx = 0
        self.peer_polling_order = self.initial_peer_polling_order

        self.short_status_order_idx = 0
        self.short_status_order = [command_table.DESTINATION_LEADER, 0, 1, 2, 3, 4, 5, 6, 7,
                                   command_table.DESTINATION_LIDAR]

        self.synchronize_image_time_across_cameras = False
        self.end_loop = False
        self.status_groups = []

        self.charge_controllers = [ChargeControllerLogger(address=settings[0], measurement_interval=settings[1],
                                                          eeprom_measurement_interval=settings[2])
                                   for settings in self.charge_controller_settings]

        peer_error_strings = [('pmc_%d_communication_error_counts' % i) for i in range(len(self.peers))]
        self.error_counter = error_counter.CounterCollection('communication_errors', self.counters_dir,
                                                             *peer_error_strings)
        self.error_counter.controller_communication_errors.reset()
        for charge_controller in self.charge_controllers:
            getattr(self.error_counter, (charge_controller.name + '_connection_error')).reset()

        self.pyro_daemon = None
        self.pyro_thread = None
        self.main_thread = None
        self.lowrate_uplink = None
        self.buffer_for_downlink = struct.pack('>255B', *([0] * 255))

        self.command_logger = command_classes.CommandLogger()

        # TODO: Set up proper destination lists, including LIDAR, narrow field, wide field, and all
        self.destination_lists = dict(enumerate([[peer] for peer in self.peers]))
        self.destination_lists[command_table.DESTINATION_ALL_CAMERAS] = self.peers
        self.destination_lists[command_table.DESTINATION_SUPER_COMMAND] = [self]

        self.setup_links()

    @property
    def leader(self):
        return self.cam_id == self.leader_id

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
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=0)
        try:
            self.pyro_daemon.shutdown()
        except Exception:
            pass
        try:
            for lowrate_uplink in self.lowrate_uplinks:
                lowrate_uplink.uplink_socket.close()
        except Exception:
            print "cant's close"
            pass
        logger.debug('Communicator deleted')

    def setup_pyro_daemon(self):
        self.pyro_daemon = Pyro4.Daemon(host='0.0.0.0', port=self.port)
        uri = self.pyro_daemon.register(self, "communicator")
        print uri

    def setup_links(self):
        # , sip_uplink_port, lowrate_downlink_ip, lowrate_downlink_port, tdrss_hirate_downlink_ip,
        # tdrss_hirate_downlink_port, tdrss_downlink_speed, openport_downlink_ipopenport_downlink_ip, openport_downlink_port,
        # openport_downlink_speed):
        self.sip_leftover_buffer = ''
        self.leftover_buffer = ''
        self.file_id = 0
        self.lowrate_uplinks = []
        self.lowrate_downlinks = []
        self.downlinks = []

        for lowrate_link_parameters in self.lowrate_link_parameters:
            self.lowrate_uplinks.append(uplink_classes.Uplink(lowrate_link_parameters[0], lowrate_link_parameters[2]))
            self.lowrate_downlinks.append(
                downlink_classes.LowrateDownlink(lowrate_link_parameters[0], *lowrate_link_parameters[1]))

        for name, (address, port), initial_rate in self.hirate_link_parameters:
            self.downlinks.append(downlink_classes.HirateDownlink(ip=address, port=port,
                                                                  speed_bytes_per_sec=initial_rate, name=name))

    ### Loops to continually be run

    def start_main_thread(self):
        self.main_thread = threading.Thread(target=self.main_loop)
        self.main_thread.daemon = True
        logger.debug('Starting leader thread')
        self.main_thread.start()

    def main_loop(self):
        while not self.end_loop:
            self.get_and_process_sip_bytes()

            if self.leader:
                self.send_data_on_downlinks()
                for charge_controller in self.charge_controllers:
                    try:
                        charge_controller.measure_and_log()
                    except ConnectionException:
                        logger.exception("Failed to connect to %s" % charge_controller.name)
                        getattr(self.error_counter, (charge_controller.name + '_connection_error')).increment()
            time.sleep(self.loop_interval)

    def peer_loop(self):
        while True:
            time.sleep(self.loop_interval)

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

    def add_status_group(self, status_group):
        self.status_groups.append(status_group)

    def send_data_on_downlinks(self):
        if not self.peers:
            raise RuntimeError(
                'Communicator has no peers. This should never happen; leader at minimum has self as peer.')  # pragma: no cover
        for link in self.downlinks:
            if link.has_bandwidth():
                if self.synchronize_image_time_across_cameras and self.peer_polling_order_idx == 0:
                    self.request_synchronized_images()
                logger.debug('Getting next data from camera %d' % self.peer_polling_order[self.peer_polling_order_idx])
                next_data = None
                active_peer = self.peers[self.peer_polling_order[self.peer_polling_order_idx]]
                try:
                    if self.check_peer_connection(active_peer):
                        next_data = active_peer.get_next_data()  # pyro call
                except Pyro4.errors.CommunicationError as e:
                    active_peer_string = str(active_peer._pyroUri)
                    error_counter_key = 'pmc_%d_communication_error_counts' % self.peer_polling_order[
                        self.peer_polling_order_idx]
                    self.error_counter.counters[error_counter_key].increment()
                    logger.debug('Connection to peer at URI %s failed. Error counter - %r. Error message: %s' % (
                        active_peer_string, self.error_counter.counters[error_counter_key], str(e)))
                except Exception as e:
                    payload = str(e)
                    payload += "".join(Pyro4.util.getPyroTraceback())
                    exception_file = file_format_classes.UnhandledExceptionFile(payload=payload,
                                                                                request_id=file_format_classes.DEFAULT_REQUEST_ID,
                                                                                camera_id=self.peer_polling_order[
                                                                                    self.peer_polling_order_idx])
                    next_data = exception_file.to_buffer()

                if not next_data:
                    logger.debug('No data was obtained.')
                else:
                    link.put_data_into_queue(next_data, self.file_id)
                    self.file_id += 1

                self.peer_polling_order_idx = (self.peer_polling_order_idx + 1) % len(self.peer_polling_order)

            else:
                if link.enabled:
                    link.send_data()

    def request_synchronized_images(self):
        timestamp = time.time() - self.synchronized_image_delay
        for peer in self.peers:
            if self.check_peer_connection(peer):
                logger.debug("Synchronizing images by requesting standard image closest to timestamp %f from peer %r" %
                             (timestamp, peer))
                queued_items = peer.get_downlink_queue_depth()  # pyro call
                if queued_items == 0:
                    peer.request_standard_image_at(timestamp)  # pyro call

    ##### Methods called by leader via pyro

    def request_standard_image_at(self, timestamp):
        try:
            self.controller.request_standard_image_at(timestamp)
        except Pyro4.errors.CommunicationError:
            self.error_counter.controller_communication_errors.increment()
            logger.debug('Connection to controller failed. Error counter - %r. Error message: %s' % (
                self.error_counter.controller_communication_errors, "".join(Pyro4.util.getPyroTraceback())))
        except Exception:
            raise Exception("".join(Pyro4.util.getPyroTraceback()))

    def get_next_data(self):
        try:
            logger.debug('Getting next data from controller.')
            return self.controller.get_next_data_for_downlink()
        except Pyro4.errors.CommunicationError:
            self.error_counter.controller_communication_errors.increment()
            logger.debug(
                'Connection to controller failed. Error counter - %r. Error message: %s' % (
                    self.error_counter.controller_communication_errors, "".join(Pyro4.util.getPyroTraceback())))
            return None
        except Exception as e:
            raise Exception(str(e) + "".join(Pyro4.util.getPyroTraceback()))

    ### The following two functions respond to SIP requests
    def respond_to_science_data_request(self, lowrate_index):
        logger.debug("Science data request received from %s." % self.lowrate_uplinks[lowrate_index].name)
        summary = self.get_next_status_summary()
        self.lowrate_downlinks[lowrate_index].send(summary)

    def check_peer_connection(self, peer):
        initial_timeout = peer._pyroTimeout
        try:
            logger.debug("Pinging peer %r" % peer)
            peer._pyroTimeout = 0.1
            peer.ping()
            return True
        except Pyro4.errors.CommunicationError:
            details = "Ping failure for peer %s" % (peer._pyroUri)
            if False:
                details += traceback.format_exc()
                pyro_details = ''.join(Pyro4.util.getPyroTraceback())
                details = details + pyro_details
            logger.warning(details)
            return False
        finally:
            peer._pyroTimeout = initial_timeout

    def process_science_command_packet(self, msg, lowrate_index):
        logger.debug('Received command with msg %r from link %d' % (msg, lowrate_index))
        try:
            command_packet = packet_classes.CommandPacket(buffer=msg)
        except (packet_classes.PacketError, ValueError) as e:
            logger.exception("Failed to decode command packet")
            return
        if command_packet.destination != command_table.DESTINATION_SUPER_COMMAND and not (self.leader):
            logger.debug("I'm not leader and this is not a super command, so I'm ignoring it")
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

    def get_next_status_summary(self):
        result = None
        while not result:
            if self.short_status_order[self.short_status_order_idx] == command_table.DESTINATION_LEADER:
                result = None
                # TODO: Fill this out
            elif self.short_status_order[self.short_status_order_idx] == command_table.DESTINATION_LIDAR:
                result = None
                # TODO: Fill this out
            else:
                peer = self.peers[self.short_status_order[self.short_status_order_idx]]
                if self.check_peer_connection(peer):
                    try:
                        summary_dict = peer.get_full_status()
                        logger.debug('Received status summary from peer %r' % peer)
                        result = self.populate_short_status_camera(summary_dict)
                    except Pyro4.errors.CommunicationError:
                        logger.debug('Unable to connect to peer %r' % peer)
                else:
                    logger.warning('Unable to connect to peer %r' % peer)
            self.short_status_order_idx += 1
            self.short_status_order_idx %= len(self.short_status_order)
        return result

    def get_full_status(self):
        summary = {}
        if self.cam_id is None:
            raise ValueError('Camera does not know its cam_id.')
        summary['cam_id'] = self.cam_id
        for group in self.status_groups:
            group.update()
            summary[group.name] = group.get_status()
        return summary

    def get_status_summary(self):
        if len(self.status_groups) == 0:
            raise RuntimeError('Communicator has no status_groups.')
        summary = []
        for group in self.status_groups:
            group.update()
            summary.append(group.get_status_summary())
        # print summary
        return summary

    def ping(self):
        return True

    ##################################################################################################
    # The following methods correspond to commands defined in pmc_turbo.communication.command_table

    def get_status_report(self, compress, request_id):
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
        json_file = file_class(payload=payload,
                               filename=('status_summary_%s.json' % time.strftime('%Y-%m-%d_%H%M%S')),
                               timestamp=time.time(),
                               camera_id=camera_id.get_camera_id(),
                               request_id=request_id)
        self.controller.add_file_to_downlink_queue(json_file.to_buffer())

    def set_peer_polling_order(self, list_argument):
        self.peer_polling_order = list_argument
        self.peer_polling_order_idx = 0

    def set_focus(self, focus_step):
        self.controller.set_focus(focus_step)

    def set_exposure(self, exposure_time_us):
        self.controller.set_exposure(exposure_time_us)

    def set_fstop(self, fstop):
        self.controller.set_fstop(fstop)

    def run_focus_sweep(self, request_id, row_offset, column_offset, num_rows, num_columns, scale_by, quality,
                        start, stop, step):
        request_params = dict(request_id=request_id, row_offset=row_offset, column_offset=column_offset,
                              num_rows=num_rows, num_columns=num_columns, scale_by=scale_by, quality=quality)
        self.controller.run_focus_sweep(request_params=request_params, start=start, stop=stop, step=step)

    def send_arbitrary_camera_command(self, command):
        try:
            parameter, value = command.split(':')
        except ValueError:
            raise ValueError("Failed to parse command string %r" % command)
        self.controller.send_arbitrary_camera_command(parameter, value)

    def set_standard_image_parameters(self, row_offset, column_offset, num_rows, num_columns, scale_by, quality):
        self.controller.set_standard_image_parameters(row_offset=row_offset, column_offset=column_offset,
                                                      num_rows=num_rows, num_columns=num_columns,
                                                      scale_by=scale_by, quality=quality)

    def request_specific_images(self, timestamp, request_id, num_images, row_offset, column_offset, num_rows,
                                num_columns,
                                scale_by, quality, step):
        self.controller.request_specific_images(timestamp=timestamp, request_id=request_id, num_images=num_images,
                                                row_offset=row_offset,
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

    def use_synchronized_images(self, synchronize):
        self.synchronize_image_time_across_cameras = bool(synchronize)

    def set_leader(self, leader_id):
        if leader_id == self.cam_id:
            self.election_enabled = False
            if not self.leader:
                self.become_leader = True
                logger.info("Becoming leader by direct command")
                self.leader_id = leader_id # TODO: this should be done gracefully in the loop when become_leader is asserted.

            else:
                logger.info("Requested to become leader, but I am already leader")
        elif leader_id == command_table.USE_BULLY_ELECTION:
            self.election_enabled = True
            logger.info("Requested to use bully election")
            # self.run_election
        else:
            if self.leader:
                # self.stop_leader_things
                logger.warning("I was leader but Camera %d has been commanded to be leader" % leader_id)
            else:
                logger.info("Camera %d has been requested to become leader," % leader_id)
            self.leader_id = leader_id
            self.election_enabled = False

    def set_downlink_bandwidth(self, openport, highrate, los):
        for link in self.downlinks:
            if link.name == 'openport':
                link.set_bandwidth(openport)
            elif link.name == 'highrate':
                link.set_bandwidth(highrate)
            elif link.name == 'los':
                link.set_bandwidth(los)
            else:
                logger.error("Unknown link %s found, so can't set its bandwidth" % link.name)

    # end command table methods
    ###################################################################################################################

    ##### SIP socket methods

    def get_and_process_sip_bytes(self):
        for i, lowrate_uplink in enumerate(self.lowrate_uplinks):
            packets = lowrate_uplink.get_sip_packets()
            for packet in packets:
                logger.debug('Found packet on lowrate link %s: %r' % (lowrate_uplink.name, packet))
                self.execute_packet(packet, i)

    def execute_packet(self, packet, lowrate_link_index):
        # Improve readability here - constants in uplink classes
        id_byte = packet[1]
        logger.debug('Got packet with id %r from uplink' % id_byte)
        if id_byte == chr(constants.SCIENCE_DATA_REQUEST_MESSAGE):
            if self.leader:
                self.respond_to_science_data_request(lowrate_link_index)
        if id_byte == chr(constants.SCIENCE_COMMAND_MESSAGE):
            self.process_science_command_packet(packet, lowrate_link_index)  ### peer methods

    ###################################################################################################################

    def populate_short_status(self, short_status_type, data_dict):
        # Populate short status class with housekeeping summary.
        if short_status_type == ShortStatusCamera:
            return self.populate_short_status_camera(data_dict)
        else:
            return self.populate_short_status_leader(data_dict)

    def populate_short_status_leader(self, data_dict):
        return

    def populate_short_status_camera(self, data_dict):

        ss = ShortStatusCamera()
        ss.message_id = 0

        kr = keyring.KeyRing(data_dict)


        ss.timestamp = kr["GevTimestampValue"]['value']
        ss.leader_id = 0  # TODO: implement self.leader_id
        ss.free_disk_root_mb = kr["df-root_df_complex-free"]['value'] / 1e6
        ss.free_disk_data_1_mb = kr["df-data1_df_complex-free"]['value'] / 1e6
        ss.free_disk_data_2_mb = kr["df-data2_df_complex-free"]['value'] / 1e6
        ss.free_disk_data_3_mb = kr["df-data3_df_complex-free"]['value'] / 1e6
        ss.free_disk_data_4_mb = kr["df-data4_df_complex-free"]['value'] / 1e6
        ss.total_images_captured = kr['total_frames']['value']
        ss.camera_packet_resent = kr["StatPacketResent"]['value']
        ss.camera_packet_missed = kr["StatPacketMissed"]['value']
        ss.camera_frames_dropped = kr["StatFrameDropped"]['value']
        ss.camera_timestamp_offset_us = kr['camera_timestamp_offset']['value']
        ss.exposure_us = (kr['ExposureTimeAbs']['value'] * 1000) - 273
        ss.focus_step = kr['EFLensFocusCurrent']['value']
        ss.aperture_times_100 = kr['EFLensFStopCurrent']['value'] * 100
        ss.pressure = 101033.3  # labjack_items['???']
        ss.lens_wall_temp = (kr['ain6']['value'] * 1000) - 273
        ss.dcdc_wall_temp = (kr['ain7']['value'] * 1000) - 273
        ss.labjack_temp = kr['temperature']['value'] - 273
        ss.camera_temp = kr['main_temperature']['value']
        ss.ccd_temp = kr['sensor_temperature']['value']
        ss.rail_12_mv = kr["ipmi_voltage-12V system_board (7.17)"]['value']
        ss.cpu_temp = kr["ipmi_temperature-CPU Temp processor (3.1)"]['value']
        ss.sda_temp = kr["hddtemp_temperature-sda"]['value']
        ss.sdb_temp = kr["hddtemp_temperature-sdb"]['value']
        ss.sdc_temp = kr["hddtemp_temperature-sdc"]['value']
        ss.sdd_temp = kr["hddtemp_temperature-sdd"]['value']
        ss.sde_temp = kr["hddtemp_temperature-sde"]['value']
        ss.sdf_temp = kr["hddtemp_temperature-sdf"]['value']
        return ss.encode()

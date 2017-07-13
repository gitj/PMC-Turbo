from __future__ import division

import collections
import json
import logging
import os
import select
import struct
import threading
import time
import traceback

import Pyro4
import Pyro4.errors
import Pyro4.socketutil
import Pyro4.util
import numpy as np
from pymodbus.exceptions import ConnectionException
from traitlets import Int, Unicode, Bool, List, Float, Tuple, TCPAddress, Enum

import pmc_turbo.housekeeping.bmon
from pmc_turbo.communication import housekeeping_classes
from pmc_turbo.communication import command_table, command_classes
from pmc_turbo.communication import constants
from pmc_turbo.communication import downlink_classes, uplink_classes, packet_classes
from pmc_turbo.communication import file_format_classes
from pmc_turbo.communication.command_table import command_manager
from pmc_turbo.communication.command_classes import CommandStatus
from pmc_turbo.communication.short_status import (ShortStatusLeader, ShortStatusCamera,
                                                  encode_one_byte_summary, decode_one_byte_summary,
                                                  no_response_one_byte_status)
from pmc_turbo.housekeeping.charge_controller import ChargeControllerLogger
from pmc_turbo.utils import error_counter, camera_id
from pmc_turbo.utils.configuration import GlobalConfiguration

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
    initial_leader_id = Int(default_value=0,min=0,max=7).tag(config=True)
    peers_with_battery_monitors = List(trait=Int).tag(config=True)
    widefield_cameras = List(trait=Int).tag(config=True)
    narrowfield_cameras=List(trait=Int).tag(config=True)
    battery_monitor_port = Unicode('/dev/ttyUSB0').tag(config=True)
    loop_interval = Float(default_value=0.01, allow_none=False, min=0).tag(config=True)
    autosend_short_status_interval = Float(default_value=30.0,min=0).tag(config=True)
    lowrate_link_parameters = List(
        trait=Tuple(Enum(("comm1", "comm2", "openport")), TCPAddress(), Int(default_value=5001, min=1024, max=65535)),
        help='List of tuples - link name, lowrate downlink address and lowrate uplink port.'
             'e.g. [("comm1",("pmc-serial-1", 5001), 5001), ...]').tag(config=True)
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

    json_paths = List(trait=Unicode,
                      help='List of paths to json files that are used to construct housekeeping classes').tag(
        config=True)

    filewatcher_threshhold_time = Float(default_value=60, allow_none=False)

    def __init__(self, cam_id, peers, controller, pyro_port, **kwargs):
        super(Communicator, self).__init__(**kwargs)
        self.port = pyro_port
        logger.debug('Communicator initialized')
        self.cam_id = cam_id
        self.leader_id = self.initial_leader_id
        self.become_leader = False
        self.battery_monitor = None

        self.peers = collections.OrderedDict()
        for peer_id, peer in peers.items():
            try:
                peer = Pyro4.Proxy(peer)
            except TypeError as e:
                if not hasattr(peer, '_pyroUri'):
                    if not hasattr(peer, 'cam_id'):
                        raise e
            self.peers[peer_id] = peer

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

        self.housekeeping = housekeeping_classes.construct_super_group_from_json_list(self.json_paths,
                                                                                      self.filewatcher_threshhold_time)

        self.synchronize_image_time_across_cameras = False
        self.end_loop = False

        self.charge_controllers = [ChargeControllerLogger(address=settings[0], measurement_interval=settings[1],
                                                          eeprom_measurement_interval=settings[2])
                                   for settings in self.charge_controller_settings]

        peer_error_strings = [('pmc_%d_communication_error_counts' % i) for i in self.peers.keys()]
        self.error_counter = error_counter.CounterCollection('communication_errors', self.counters_dir,
                                                             *peer_error_strings)
        self.error_counter.controller_communication_errors.reset()
        for charge_controller in self.charge_controllers:
            getattr(self.error_counter, (charge_controller.name + '_connection_error')).reset()
        self.error_counter.battery_monitor_error.reset()

        self.pyro_daemon = None
        self.pyro_thread = None
        self.main_thread = None
        self.lowrate_uplink = None
        self.buffer_for_downlink = struct.pack('>255B', *([0] * 255))

        self.last_autosend_timestamp = 0

        self.command_logger = command_classes.CommandLogger()

        # TODO: Set up proper destination lists, including LIDAR, narrow field, wide field, and all
        self.destination_lists = dict([(peer_id, [peer]) for (peer_id, peer) in self.peers.items()])
        self.destination_lists[command_table.DESTINATION_SUPER_COMMAND] = [self]
        self.destination_lists[command_table.DESTINATION_NARROWFIELD_CAMERAS] = [self.peers[index] for index in self.narrowfield_cameras]
        self.destination_lists[command_table.DESTINATION_WIDEFIELD_CAMERAS] = [self.peers[index] for index in self.widefield_cameras]
        self.destination_lists[command_table.DESTINATION_ALL_CAMERAS] = (self.destination_lists[command_table.DESTINATION_NARROWFIELD_CAMERAS]+
                                                                         self.destination_lists[command_table.DESTINATION_WIDEFIELD_CAMERAS])

        self.setup_links()

        if self.cam_id in self.peers_with_battery_monitors:
            if os.path.exists(self.battery_monitor_port):
                self.battery_monitor = pmc_turbo.housekeeping.bmon.Monitor(port=self.battery_monitor_port,
                                                                       log_dir=os.path.join(self.housekeeping_dir,'battery'))
                try:
                    self.battery_monitor.create_files()
                except Exception:
                    logger.exception("Failure while creating battery monitor log files!")
            else:
                logger.exception("This camera is in the list of cameras with battery monitors, "
                                 "but the specified battery monitor port does not exist!")


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
        self.downlinks = collections.OrderedDict()

        for lowrate_link_parameters in self.lowrate_link_parameters:
            self.lowrate_uplinks.append(uplink_classes.Uplink(lowrate_link_parameters[0], lowrate_link_parameters[2]))
            self.lowrate_downlinks.append(
                downlink_classes.LowrateDownlink(lowrate_link_parameters[0], *lowrate_link_parameters[1]))

        for name, (address, port), initial_rate in self.hirate_link_parameters:
            self.downlinks[name] = downlink_classes.HirateDownlink(ip=address, port=port,
                                                                   speed_bytes_per_sec=initial_rate, name=name)

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
                self.send_short_status_periodically_via_highrate()
                self.send_data_on_downlinks()
                for charge_controller in self.charge_controllers:
                    try:
                        charge_controller.measure_and_log()
                    except ConnectionException:
                        logger.exception("Failed to connect to %s" % charge_controller.name)
                        getattr(self.error_counter, (charge_controller.name + '_connection_error')).increment()
            if self.battery_monitor:
                try:
                    self.battery_monitor.measure_and_log()
                except Exception:
                    logger.exception("Failure while monitoring battery")
                    self.error_counter.battery_monitor_error.increment()
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

    def send_short_status_periodically_via_highrate(self):
        if time.time() - self.last_autosend_timestamp > self.autosend_short_status_interval:
            short_status_approx_bytes_per_second = 100. / self.autosend_short_status_interval
            for name,link in self.downlinks.items():
                if link.downlink_speed_bytes_per_sec > short_status_approx_bytes_per_second:
                    next_data = file_format_classes.ShortStatusFile(payload=self.get_next_status_summary(),
                                                                    request_id=file_format_classes.DEFAULT_REQUEST_ID,
                                                                    camera_id=self.cam_id).to_buffer()
                    self.last_autosend_timestamp = time.time()
                    logger.info("Sending short status via %s with file_id %d" % (name,self.file_id))
                    link.put_data_into_queue(next_data,self.file_id,preempt=True)
                    self.file_id += 1
                else:
                    logger.debug("Skipping sending short status on link %s because bandwidth %f bytes/s is insufficient"
                                 % (name,link.downlink_speed_bytes_per_sec))


    def send_data_on_downlinks(self):
        if not self.peers:
            raise RuntimeError(
                'Communicator has no peers. This should never happen; leader at minimum has self as peer.')  # pragma: no cover
        for link in self.downlinks.values():
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
        for peer in self.peers.values():
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
        logger.debug("sending lowrate status %d bytes, message id %d" % (len(summary), ord(summary[0])))
        self.lowrate_downlinks[lowrate_index].send(summary)

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
        alive_destinations = []
        for number, destination in enumerate(destinations):
            try:
                logger.debug("pinging destination %d member %d" % (command_packet.destination, number))
                destination.ping()
                alive_destinations.append(destination)
            except Exception as e:
                details = "Ping failure for destination %d, member %d\n" % (command_packet.destination, number)
                details += traceback.format_exc()
                pyro_details = ''.join(Pyro4.util.getPyroTraceback())
                details = details + pyro_details
                self.command_logger.add_command_result(command_packet.sequence_number,
                                                       CommandStatus.failed_to_ping_destination,
                                                       details)
                logger.warning(details)
                continue

        command_name = "<Unknown>"
        number = 0
        kwargs = {}
        try:
            commands = command_manager.decode_commands(command_packet.payload)
            for number, destination in enumerate(alive_destinations):
                for command_name, kwargs in commands:
                    logger.debug("Executing command %s at destination %d member %d peer %r with kwargs %r" % (command_name,
                                                                                                      command_packet.destination,
                                                                                                      number, destination, kwargs))
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
            next_status_index = self.short_status_order[self.short_status_order_idx]
            if next_status_index == command_table.DESTINATION_LEADER:
                result = self.populate_short_status_leader()
                logger.debug("got leader status, message id %d" % ord(result[0]))
            elif next_status_index == command_table.DESTINATION_LIDAR:
                result = None
                # TODO: Fill this out
            elif next_status_index in self.peers:
                peer = self.peers[next_status_index]
                if self.check_peer_connection(peer):
                    try:
                        result = peer.get_short_status_camera()
                        logger.debug("got peer status, message id %d" % ord(result[0]))
                    except Pyro4.errors.CommunicationError:
                        logger.debug('Unable to connect to peer %r' % peer)
                else:
                    logger.warning('Unable to connect to peer %r' % peer)
            else:
                result = None
            self.short_status_order_idx += 1
            self.short_status_order_idx %= len(self.short_status_order)
        return result

    def ping(self):
        return True

    def check_peer_connection(self, peer):
        initial_timeout = peer._pyroTimeout
        try:
            logger.debug("Pinging peer %r" % peer)
            peer._pyroTimeout = 0.1
            peer.ping()
            return True
        except Pyro4.errors.CommunicationError:
            details = "Ping failure for peer %s" % (peer._pyroUri)
            logger.warning(details)
            return False
        finally:
            peer._pyroTimeout = initial_timeout

    ##################################################################################################
    # The following methods correspond to commands defined in pmc_turbo.communication.command_table
    # Cannot remove these commands without also removing them from the command table.
    # DISCUSS WITH GROUP BEFORE CHANGING COMMANDS

    def get_status_report(self, compress, request_id):
        logger.debug('Status report requested')
        summary = []

        # NOTE: When LIDAR and leader housekeeping is added, summary should also append those statuses.
        self.housekeeping.update()
        summary.append(self.housekeeping.get_three_column_data_set())
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

    def get_command_history(self, request_id):
        payload = json.dumps(self.command_logger.command_history)
        json_file = file_format_classes.CompressedJSONFile(payload=payload,
                                                           filename=(
                                                               'command_history_%s.json' % time.strftime(
                                                                   '%Y-%m-%d_%H%M%S')),
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
        for link in self.downlinks.values():
            link.flush_packet_queue()

    def use_synchronized_images(self, synchronize):
        self.synchronize_image_time_across_cameras = bool(synchronize)

    def set_leader(self, leader_id):
        if leader_id == self.cam_id:
            self.election_enabled = False
            if not self.leader:
                self.become_leader = True
                logger.info("Becoming leader by direct command")
                self.leader_id = leader_id  # TODO: this should be done gracefully in the loop when become_leader is asserted.

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
        for name, link in self.downlinks.items():
            if name == 'openport':
                link.set_bandwidth(openport)
            elif name == 'highrate':
                link.set_bandwidth(highrate)
            elif name == 'los':
                link.set_bandwidth(los)
            else:
                logger.error("Unknown link %s found, so can't set its bandwidth" % name)

    def set_auto_exposure_parameters(self,max_percentile_threshold_fraction,
                                     min_peak_threshold_fraction,
                                     min_percentile_threshold_fraction,
                                     adjustment_step_size_fraction,
                                     min_exposure,
                                     max_exposure):
        self.controller.set_auto_exposure_parameters(max_percentile_threshold_fraction=max_percentile_threshold_fraction,
                                     min_peak_threshold_fraction=min_peak_threshold_fraction,
                                     min_percentile_threshold_fraction=min_percentile_threshold_fraction,
                                     adjustment_step_size_fraction=adjustment_step_size_fraction,
                                     min_exposure=min_exposure,
                                     max_exposure=max_exposure)

    def enable_auto_exposure(self,enabled):
        self.controller.enable_auto_exposure(enabled)

    def request_blobs_by_timestamp(self, timestamp, request_id, num_images, step, stamp_size,
                          blob_threshold, kernel_sigma, kernel_size, cell_size, max_num_blobs,
                          quality):
        self.controller.request_blobs_by_timestamp(timestamp=timestamp, request_id=request_id, num_images=num_images,
                                                   step=step, stamp_size=stamp_size, blob_threshold=blob_threshold,
                                                   kernel_sigma=kernel_sigma, kernel_size=kernel_size,
                                                   cell_size=cell_size, max_num_blobs=max_num_blobs, quality=quality)

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
        id_byte = packet[1]
        logger.debug('Got packet with id %r from uplink' % id_byte)
        if id_byte == chr(constants.SCIENCE_DATA_REQUEST_MESSAGE):
            if self.leader:
                self.respond_to_science_data_request(lowrate_link_index)
        if id_byte == chr(constants.SCIENCE_COMMAND_MESSAGE):
            self.process_science_command_packet(packet, lowrate_link_index)  ### peer methods

    ###################################################################################################################

    def one_byte_summary(self, timestamp):
        clock_offset = time.time() - timestamp
        try:
            depth = self.controller.get_downlink_queue_depth()
            controller_alive = True
        except Pyro4.errors.CommunicationError:
            depth = 0
            controller_alive = False
        status = None
        if controller_alive:
            try:
                status = self.controller.get_pipeline_status()
            except Pyro4.errors.CommunicationError:
                pass
        pipeline_alive = (status is not None)
        time_synced = np.abs(clock_offset) < 1
        if status:
            ptp_synced = np.abs(status['camera_timestamp_offset']) < 2000

            write_enable = (status['disk write enable 0'] or status['disk write enable 1'] or
                            status['disk write enable 2'] or status['disk write enable 3'])
            writing_images = (write_enable and
                              (status['disk 0'] != 'exiting') and (status['disk 1'] != 'exiting') and
                              (status['disk 2'] != 'exiting') and (status['disk 3'] != 'exiting'))
            taking_images = False  # TODO: implement this
        else:
            ptp_synced = False
            writing_images = False
            taking_images = False

        return encode_one_byte_summary(is_leader=self.leader,
                                       controller_alive=controller_alive,
                                       pipeline_alive=pipeline_alive,
                                       files_to_downlink=bool(depth),
                                       ptp_synced=ptp_synced,
                                       time_synced=time_synced,
                                       taking_images=taking_images,
                                       writing_images=writing_images)

    def populate_short_status_leader(self):
        ss = ShortStatusLeader()
        ss.timestamp = time.time()
        ss.leader_id = self.leader_id  # since we're sending this, leader_id == camera_id

        ss.status_byte_camera_0 = no_response_one_byte_status
        ss.status_byte_camera_1 = no_response_one_byte_status
        ss.status_byte_camera_2 = no_response_one_byte_status
        ss.status_byte_camera_3 = no_response_one_byte_status
        ss.status_byte_camera_4 = no_response_one_byte_status
        ss.status_byte_camera_5 = no_response_one_byte_status
        ss.status_byte_camera_6 = no_response_one_byte_status
        ss.status_byte_camera_7 = no_response_one_byte_status

        for peer_id, peer in self.peers.items():
            connected = self.check_peer_connection(peer)
            if connected:
                try:
                    status = peer.one_byte_summary(time.time())
                    logger.info("peer %d is connected and has status %02X:\n%r" % (
                        peer_id, status, decode_one_byte_summary(status)))
                except Pyro4.errors.CommunicationError:
                    logger.exception("Failed to get one byte status from peer %d after successful ping" % peer_id)
                    status = no_response_one_byte_status
            else:
                status = no_response_one_byte_status
                logger.warning("peer %d is not connected, setting status %02X" % (peer_id, status))
            setattr(ss, ('status_byte_camera_%d' % peer_id), status)

        ss.status_byte_lidar = no_response_one_byte_status

        result = self.command_logger.get_latest_result()
        if result is None:
            last_sequence = np.nan
        else:
            last_sequence = result[1]
        ss.last_command_sequence = last_sequence
        result = self.command_logger.get_highest_sequence_number_result()
        if result is None:
            highest_sequence = np.nan
        else:
            highest_sequence = result[1]
        ss.highest_command_sequence = highest_sequence
        sequence_skip = self.command_logger.get_last_sequence_skip()
        if sequence_skip is None:
            sequence_skip = np.nan
        ss.last_outstanding_sequence = sequence_skip
        ss.total_commands_received = self.command_logger.total_commands_received
        result = self.command_logger.get_last_failed_result()
        last_failed_sequence = np.nan
        if result and result[2]:
            last_failed_sequence = result[1]
        ss.last_failed_sequence = last_failed_sequence

        ss.current_file_id = self.file_id

        highrate_link = self.downlinks['highrate']
        ss.bytes_sent_highrate = highrate_link.total_bytes_sent
        ss.packets_queued_highrate = len(highrate_link.packets_to_send)
        ss.bytes_per_sec_highrate = highrate_link.downlink_speed_bytes_per_sec

        openport_link = self.downlinks['openport']
        ss.bytes_sent_openport = openport_link.total_bytes_sent
        ss.packets_queued_openport = len(openport_link.packets_to_send)
        ss.bytes_per_sec_openport = openport_link.downlink_speed_bytes_per_sec

        los_link = self.downlinks['los']
        ss.bytes_sent_los = los_link.total_bytes_sent
        ss.packets_queued_los = len(los_link.packets_to_send)
        ss.bytes_per_sec_los = los_link.downlink_speed_bytes_per_sec

        ss.charge_cont_1_solar_voltage = np.nan
        ss.charge_cont_1_solar_current = np.nan
        ss.charge_cont_1_battery_voltage = np.nan
        ss.charge_cont_1_battery_current = np.nan
        ss.charge_cont_1_battery_temp = np.nan
        ss.charge_cont_1_heatsink_temp = np.nan

        ss.charge_cont_2_solar_voltage = np.nan
        ss.charge_cont_2_solar_current = np.nan
        ss.charge_cont_2_battery_voltage = np.nan
        ss.charge_cont_2_battery_current = np.nan
        ss.charge_cont_2_battery_temp = np.nan
        ss.charge_cont_2_heatsink_temp = np.nan

        return ss.encode()

    def get_short_status_camera(self):

        ss = ShortStatusCamera()
        ss.message_id = self.cam_id

        self.housekeeping.update()

        # The 0th index of the tuple is the epoch, the 1st is the value

        ss.timestamp = time.time()
        ss.leader_id = self.leader_id
        ss.free_disk_root_mb = self.housekeeping.get_recent_value("df-root_df_complex-free") / 1e6
        ss.free_disk_var_mb = self.housekeeping.get_recent_value("df-var_df_complex-free") / 1e6
        ss.free_disk_data_1_mb = self.housekeeping.get_recent_value("df-data1_df_complex-free") / 1e6
        ss.free_disk_data_2_mb = self.housekeeping.get_recent_value("df-data2_df_complex-free") / 1e6
        ss.free_disk_data_3_mb = self.housekeeping.get_recent_value("df-data3_df_complex-free") / 1e6
        ss.free_disk_data_4_mb = self.housekeeping.get_recent_value("df-data4_df_complex-free") / 1e6
        ss.free_disk_data_5_mb = self.housekeeping.get_recent_value("df-data5_df_complex-free") / 1e6
        ss.total_images_captured = self.housekeeping.get_recent_value('total_frames')
        ss.camera_packet_resent = self.housekeeping.get_recent_value("StatPacketResent")
        ss.camera_packet_missed = self.housekeeping.get_recent_value("StatPacketMissed")
        ss.camera_frames_dropped = self.housekeeping.get_recent_value("StatFrameDropped")
        ss.camera_timestamp_offset_us = self.housekeeping.get_recent_value('camera_timestamp_offset')
        ss.exposure_us = self.housekeeping.get_recent_value('ExposureTimeAbs')
        ss.focus_step = self.housekeeping.get_recent_value('EFLensFocusCurrent')
        ss.aperture_times_100 = self.housekeeping.get_recent_value('EFLensFStopCurrent') * 100
        try:
            ss.auto_exposure_enabled = self.controller.is_auto_exposure_enabled()
        except Exception:
            logger.exception("Failed to get auto_exposure_enabled from controller")
            ss.auto_exposure_enabled = np.nan
        ss.pressure = self.housekeeping.get_recent_value("Pressure")
        ss.lens_wall_temp = (self.housekeeping.get_recent_value('Lens_Temperature') * 1000) - 273
        ss.dcdc_wall_temp = (self.housekeeping.get_recent_value('DCDC_Temperature') * 1000) - 273
        ss.labjack_temp = self.housekeeping.get_recent_value('Labjack_Temperature') - 273
        ss.camera_temp = self.housekeeping.get_recent_value('main_temperature')
        ss.ccd_temp = self.housekeeping.get_recent_value('sensor_temperature')
        ss.rail_12_mv = self.housekeeping.get_recent_value("ipmi_voltage-12V system_board (7.17)") * 1000
        ss.cpu_temp = self.housekeeping.get_recent_value("ipmi_temperature-CPU Temp processor (3.1)")
        ss.sda_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sda")
        ss.sdb_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sdb")
        ss.sdc_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sdc")
        ss.sdd_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sdd")
        ss.sde_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sde")
        ss.sdf_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sdf")
        ss.sdg_temp = self.housekeeping.get_recent_value("hddtemp_temperature-sdg")
        return ss.encode()

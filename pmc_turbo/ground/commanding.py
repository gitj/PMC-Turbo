import os
import socket
import logging

import serial
import time
from traitlets import Float
from pmc_turbo.communication.command_table import command_manager

from pmc_turbo.communication.packet_classes import (CommandPacket,
                                                    GSECommandPacket,
                                                    PacketError,
                                                    decode_gse_acknowledgement,
                                                    gse_acknowledgment_codes,
                                                    gse_acknowledgment_length)
from pmc_turbo.ground.ground_configuration import GroundConfiguration

logger = logging.getLogger(__name__)

LOS1 = GSECommandPacket.LOS1
LOS2 = GSECommandPacket.LOS2
TDRSS = GSECommandPacket.TDRSS
IRIDIUM = GSECommandPacket.IRIDIUM

OPENPORT = 'openport'
link_ids = {LOS1: 'los1', LOS2: 'los2', TDRSS: 'tdrss', IRIDIUM: 'iridium', OPENPORT: 'openport'}


class CommandHistoryLogger(GroundConfiguration):
    column_names = ['send_timestamp', 'sequence_number', 'num_commands', 'destination',
                    'link_id', 'acknowledgement_code', 'send_successful', 'command_blob_file']

    def __init__(self, **kwargs):
        super(CommandHistoryLogger, self).__init__(**kwargs)
        timestring = time.strftime('%Y-%m-%d_%H%M%S')
        self.command_history_path = os.path.join(self.root_data_path, self.command_history_subdir, timestring)
        os.makedirs(self.command_history_path)
        self.command_history_index_filename = os.path.join(self.command_history_path,'index.csv')
        self.create_command_history_index_file()

    def create_command_history_index_file(self):
        with open(self.command_history_index_filename, 'w') as fh:
            fh.write(','.join(self.column_names) + '\n')

    def write_row(self, send_timestamp, sequence_number, num_commands, destination, link_id, acknowledgement_code,
                  send_successful, command_blob):
        command_blob_file = self.write_command_blob(send_timestamp, sequence_number, command_blob)
        with open(self.command_history_index_filename, 'a') as fh:
            fh.write(
                ','.join([str(x) for x in (send_timestamp, sequence_number, num_commands, destination, link_id, acknowledgement_code,
                          send_successful, command_blob_file)]) + '\n')

    def write_command_blob(self, timestamp, sequence_number, command_blob):
        timestring = time.strftime('%Y-%m-%d_%H%M%S', time.localtime(timestamp))
        filename = os.path.join(self.command_history_path, ('%s_%05d' % (timestring, sequence_number)))
        with open(filename, 'w') as fh:
            fh.write(command_blob)
        return filename


class CommandSender(GroundConfiguration):
    command_port_baudrate = 2400  # LDB 2.1.2
    command_port_response_timeout = Float(3., help="Timeout for serial command port. This sets how much time is "
                                                   "allocated for the GSE to acknowledge the command we sent.",
                                          min=0).tag(config=True)

    def __init__(self, **kwargs):
        super(CommandSender, self).__init__(**kwargs)

        self.command_manager = command_manager
        self.openport_link = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.command_port:
            self.serial_port = serial.Serial(self.command_port, baudrate=self.command_port_baudrate,
                                             timeout=self.command_port_response_timeout)
        else:
            self.serial_port = None
        self.current_link = OPENPORT
        self.history_logger = CommandHistoryLogger(**kwargs)
        self.sequence_number_filename = os.path.join(self.root_data_path, 'next_command_sequence_number')
        try:
            with open(self.sequence_number_filename) as fh:
                self.next_sequence_number = int(fh.read())
                logger.info("Read next command sequence number %d from disk" % self.next_sequence_number)
        except Exception as e:
            logger.exception("Could not read next command sequence number from disk, starting at zero")
            self.next_sequence_number = 0
        for command in command_manager._command_dict.values():
            setattr(self, command.name, command)

    def set_link_openport(self):
        self.current_link = OPENPORT

    def set_link_los1(self):
        self.current_link = LOS1

    def set_link_los2(self):
        self.current_link = LOS2

    def set_link_tdrss(self):
        self.current_link = TDRSS

    def set_link_iridium(self):
        self.current_link = IRIDIUM

    def send(self, payload, destination, via=None):
        commands = command_manager.decode_commands(payload)
        result = None
        if via is None:
            via = self.current_link

        message = ''
        if via == OPENPORT:
            packet = CommandPacket(payload=payload, sequence_number=self.next_sequence_number, destination=destination)
            command_blob = packet.to_buffer()
            timestamp = time.time()
            try:
                self.openport_link.sendto(command_blob, self.openport_uplink_address)
                acknowledgement_code = 0x00
                send_successful = 1
            except socket.error:
                logger.exception("Failed to send command sequence number %d" % self.next_sequence_number)
                acknowledgement_code = 0xFF
                send_successful = 0


        elif via in [LOS1, LOS2, TDRSS, IRIDIUM]:
            packet = GSECommandPacket(payload=payload, sequence_number=self.next_sequence_number,
                                      destination=destination,
                                      link_tuple=via)
            command_blob = packet.to_buffer()
            timestamp = time.time()
            self.serial_port.write(command_blob)
            response = self.serial_port.read(gse_acknowledgment_length)
            if response != '':
                try:
                    acknowledgement_code, remainder = decode_gse_acknowledgement(response)
                    if acknowledgement_code == 0x00:
                        send_successful = 1
                    else:
                        send_successful = 0
                except PacketError:
                    logger.exception("Failed to decode GSE response %r to command sequence number %d" %( response, self.next_sequence_number))
                    acknowledgement_code = 0xFF
                    send_successful = 0
            else:
                message = "No response received from GSE!"
                acknowledgement_code = 0xFF
                send_successful = 0
        else:
            raise ValueError("Unknown uplink specified %r" % via)

        if not message:
            message = gse_acknowledgment_codes.get(acknowledgement_code,'Unknown exception occurred while sending or decoding GSE response')
        if send_successful:
            logger.info("Successfully sent command sequence %d via %s with destination %d"
                        % (self.next_sequence_number, link_ids[via], destination))
        else:
            logger.error("Failed to send command sequence %d via %s!\n\tMessage: %s"
                             % (self.next_sequence_number, link_ids[via], message))

        self.history_logger.write_row(send_timestamp=timestamp, sequence_number=self.next_sequence_number,
                                      num_commands=len(commands), destination=destination, link_id=link_ids[via],
                                      acknowledgement_code=acknowledgement_code, send_successful=send_successful,
                                      command_blob=command_blob)
        self.next_sequence_number += 1
        try:
            with open(self.sequence_number_filename, 'w') as fh:
                fh.write('%d' % self.next_sequence_number)
                logger.debug("Next command sequence number %d written to disk" % self.next_sequence_number)
        except Exception:
            logger.exception("Could not write next command sequence number %d to disk" % self.next_sequence_number)
        return result

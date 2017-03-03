import socket

import serial
from traitlets import Float
from pmc_turbo.communication.command_table import command_manager

from pmc_turbo.communication.packet_classes import (CommandPacket,
                                                    GSECommandPacket,
                                                    decode_gse_acknowledgement,
                                                    gse_acknowledgment_codes,
                                                    gse_acknowledgment_length)
from pmc_turbo.ground.ground_configuration import GroundConfiguration

LOS1 = GSECommandPacket.LOS1
LOS2 = GSECommandPacket.LOS2
TDRSS = GSECommandPacket.TDRSS
IRIDIUM = GSECommandPacket.IRIDIUM

OPENPORT = 'openport'

class CommandSender(GroundConfiguration):
    command_port_baudrate = 2400  # LDB 2.1.2
    command_port_response_timeout = Float(3.,help="Timeout for serial command port. This sets how much time is allocated "
                                                  "for the GSE to acknowledge the command we sent.", min=0).tag(config=True)
    def __init__(self,**kwargs):
        super(CommandSender,self).__init__(**kwargs)
        self.command_manager = command_manager
        self.openport_link = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        if self.command_port:
            self.serial_port = serial.Serial(self.command_port,baudrate=self.command_port_baudrate,
                                             timeout=self.command_port_response_timeout)
        else:
            self.serial_port = None
        self.current_link = OPENPORT
        self.next_sequence_number=0
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
        result = None
        if via is None:
            via = self.current_link
        if via == OPENPORT:
            link = self.openport_link
            packet = CommandPacket(payload=payload,sequence_number=self.next_sequence_number,destination=destination)
            print '%r' % packet.to_buffer()
            link.sendto(packet.to_buffer(),self.openport_uplink_address)
            print len(packet)
        elif via in [LOS1, LOS2, TDRSS, IRIDIUM]:
            link = self.serial_port
            packet = GSECommandPacket(payload=payload,sequence_number=self.next_sequence_number,destination=destination,
                                      link_tuple=via)
            print '%r' % packet.to_buffer()
            link.write(packet.to_buffer())
            response = link.read(gse_acknowledgment_length)
            result,remainder = decode_gse_acknowledgement(response)
            print gse_acknowledgment_codes[result],remainder, len(packet)
        else:
            raise ValueError("Unknown uplink specified %r" % via)
        self.next_sequence_number += 1
        return result

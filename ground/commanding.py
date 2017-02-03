import socket
import serial

from pmc_camera.communication.command_table import command_manager
from pmc_camera.communication.packet_classes import CommandPacket,GSECommandPacket, decode_gse_acknowledgement, gse_acknowledgment_codes
LOS1 = GSECommandPacket.LOS1
LOS2 = GSECommandPacket.LOS2
TDRSS = GSECommandPacket.TDRSS
IRIDIUM = GSECommandPacket.IRIDIUM

OPEN_PORT = 'open_port'

class CommandSender(object):
    def __init__(self,open_port_address, serial_port_device):
        '''

        Parameters
        ----------
        open_port_address: tuple string ip_address, int port
        serial_port_device: string serial_port

        '''
        self.command_manager = command_manager
        self.open_port_link = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.open_port_address = open_port_address
        if serial_port_device:
            self.serial_port = serial.Serial(serial_port_device,baudrate=2400,timeout=3)
        else:
            self.serial_port = None
        self.current_link = OPEN_PORT
        self.next_sequence_number=0
        for command in command_manager._command_dict.values():
            setattr(self, command.name, command)

    def set_link_openport(self):
        self.current_link = OPEN_PORT

    def set_link_los1(self):
        self.current_link = LOS1

    def set_link_los2(self):
        self.current_link = LOS2

    def set_link_tdrss(self):
        self.current_link = TDRSS

    def set_link_iridium(self):
        self.current_link = IRIDIUM

    def send(self, payload, destination, via=None):
        if via is None:
            via = self.current_link
        if via == OPEN_PORT:
            link = self.open_port_link
            packet = CommandPacket(payload=payload,sequence_number=self.next_sequence_number,destination=destination)
            print '%r' % packet.to_buffer()
            link.sendto(packet.to_buffer(),self.open_port_address)
            self.next_sequence_number += 1
            return None
        elif via in [LOS1, LOS2, TDRSS, IRIDIUM]:
            link = self.serial_port
            packet = GSECommandPacket(payload=payload,sequence_number=self.next_sequence_number,destination=destination,
                                      link_tuple=via)
            print '%r' % packet.to_buffer()
            link.write(packet.to_buffer())
            response = link.read(3)
            result = decode_gse_acknowledgement(response)
            print gse_acknowledgment_codes[result]
            return result

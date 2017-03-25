"""
        telemetry format:
                struct frame_header {
                        uint16_t        start_marker;   // 0x78 0x78
                        uint16_t        frame_counter;
                        uint8_t         frame_type;
                        uint32_t        onboard_time;   // 20 bits onboard_time,
                                                        // 12 bits data_length
                        uint8_t         data_length;    // 12+8 = 20 bits data_length
                        uint16_t        crc;
                };
                and payload:
                        data_length = 5315 byte for telemetry mode 1
                        data_length = 5415 byte for telemetry mode 2
                        sizes may change in future

"""
import struct
import socket
from traitlets import Int,TCPAddress
from pmc_turbo.utils.configuration import GlobalConfiguration
import logging
from pmc_turbo.communication.packet_classes import LidarTelemetryPacket, PacketInsufficientLengthError, PacketChecksumError, PacketError

logger = logging.getLogger(__name__)

slow_telemetry_request = """0,A,T
0 COLOSSUS:SLOWTEL
END 1632
"""


class LidarTelemetry(GlobalConfiguration):
    telemetry_address = TCPAddress(default_value=('sirius.kaifler.net',9007)).tag(config=True)
    slow_telemetry_port = Int(9008,min=1024,max=65535).tag(config=True)
    def __init__(self,**kwargs):
        super(LidarTelemetry,self).__init__(**kwargs)
        self.telemetry_socket = None
        self.slow_telemetry_socket = None
        self.packet_in_progress = ''

    def connect(self):
        try:
            self.telemetry_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.telemetry_socket.bind(('',self.telemetry_address[1]))
            self.telemetry_socket.connect(self.telemetry_address)
            self.telemetry_socket.settimeout(1)
            self.slow_telemetry_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.slow_telemetry_socket.bind(('',self.slow_telemetry_port))
            self.slow_telemetry_socket.connect((self.telemetry_address[0],self.slow_telemetry_port))
            self.slow_telemetry_socket.settimeout(1)
        except socket.error:
            logger.exception("Couldn't open sockets")
            self.close()
    def close(self):
        if self.telemetry_socket:
            try:
                self.telemetry_socket.close()
            except Exception as e:
                logger.exception("Failure while closing telemetry socket")
            self.telemetry_socket = None
        if self.slow_telemetry_socket:
            try:
                self.slow_telemetry_socket.close()
            except Exception as e:
                logger.exception("Failure while closing slow telemetry socket")
            self.slow_telemetry_socket = None


    def get_telemetry_data(self):
        try:
            packet = self.telemetry_socket.recv(8192)
        except socket.error as e:
            print "socket error receivng telemetry", e
            packet = ''

        if not packet:
            return None
        lidar_packet = None
        try:
            lidar_packet = LidarTelemetryPacket(buffer=packet)
            print "got valid packet from single TCP packet",lidar_packet.frame_counter, lidar_packet.payload_length
            self.packet_in_progress = ''
            return lidar_packet
        except PacketError:
            pass
        trial_data = self.packet_in_progress + packet
        try:
            lidar_packet = LidarTelemetryPacket(buffer=trial_data)
            print "got valid packet!", lidar_packet.frame_counter, lidar_packet.payload_length
            self.packet_in_progress = ''
            return lidar_packet
        except PacketInsufficientLengthError as e:
            logger.debug(str(e))
            self.packet_in_progress = trial_data
            return None
        except PacketError as e:
            self.packet_in_progress = ''
            logger.debug(str(e))
            return None

    def get_slow_telemetry_data(self):
        try:
            packet = self.slow_telemetry_socket.recv(8192)
        except socket.error as e:
            print "no slow data",e
            return None
        return packet

    def request_and_get_slow_telemetry(self):
        self.telemetry_socket.sendall(slow_telemetry_request)
        return self.get_slow_telemetry_data()


    def run(self):
        if self.telemetry_socket is None:
            self.connect()
        while True:
            print self.request_and_get_slow_telemetry()
#            telemetry = self.get_telemetry_data()
#            slow = self.get_slow_telemetry_data()
#            if slow:
#                print slow
#            self.telemetry_socket.sendall(slow_telemetry_request)




if __name__ == "__main__":
    lt = LidarTelemetry()
    lt.run()
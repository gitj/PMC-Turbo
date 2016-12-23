from __future__ import division
import time
import socket
import struct
import numpy as np
from pmc_camera.communication import packet_classes
from pmc_camera.communication.hirate import cobs_encoding


class HirateDownlink():
    def __init__(self, downlink_ip, downlink_port, downlink_speed):
        self.downlink_ip, self.downlink_port = downlink_ip, downlink_port
        self.downlink_speed = downlink_speed
        self.prev_packet_size = 0
        self.prev_packet_time = 0
        self.packets_to_send = []
        self.enabled = True

    def put_data_into_queue(self, buffer, file_id, file_type, packet_size=1000):
        print len(buffer)
        packets = []
        num_packets = np.ceil(len(buffer) / packet_size)
        for i in range(int(num_packets)):
            msg = buffer[(i * packet_size):((i + 1) * packet_size)]
            encoded_msg = cobs_encoding.encode_data(msg, 0xFA)
            packet = packet_classes.HiratePacket(file_id=file_id, file_type=file_type, packet_number=i,
                                                 total_packet_number=num_packets, payload=encoded_msg)
            packets.append(packet)
        for packet in packets:
            print packet.payload_length
        print np.sum([packet.payload_length for packet in packets])
        self.packets_to_send += packets

    def send_data(self):
        wait_time = self.prev_packet_size / self.downlink_speed
        if time.time() - self.prev_packet_time > wait_time:
            buffer = self.packets_to_send[0].to_buffer()
            if buffer.find(chr(0xFA)):
                raise AttributeError('Start byte found within buffer.')
            self.send(buffer, self.downlink_ip, self.downlink_port)
            self.prev_packet_size = len(buffer)
            self.prev_packet_time = time.time()
            self.packets_to_send = self.packets_to_send[1:]

    def send(self, msg, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = sock.sendto(msg, (ip, port))
        print data
        sock.close()

    def has_bandwidth(self):
        return self.enabled and not self.packets_to_send


class LowrateDownlink():
    HEADER = '\x10\x53'
    FOOTER = '\x03'

    def __init__(self, downlink_ip, downlink_port):
        self.downlink_ip, self.downlink_port = downlink_ip, downlink_port

    def _send(self, msg):
        # sip_downlink_ip='192.168.1.54', sip_downlink_port=4001 in our experimental setup.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg, (self.downlink_ip, self.downlink_port))
        sock.close()

    def send(self, msg):
        format_string = '1B%ds' % len(msg)
        msg = struct.pack(format_string, len(msg), msg)
        msg = self.HEADER + msg + self.FOOTER
        # logger.debug('Message to be sent to downlink: %r' % msg)
        self._send(msg)

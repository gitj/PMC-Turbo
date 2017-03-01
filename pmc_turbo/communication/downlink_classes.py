from __future__ import division

import logging
import socket
import struct
import time

import numpy as np
from pmc_turbo.communication import packet_classes

import constants

logger = logging.getLogger(__name__)


class HirateDownlink():
    def __init__(self, ip, port, speed_bytes_per_sec, name):
        self.downlink_ip, self.downlink_port = ip, port
        self.downlink_speed_bytes_per_sec = speed_bytes_per_sec
        self.prev_packet_size = 0
        self.prev_packet_time = 0
        self.packets_to_send = []
        self.enabled = True
        self.name = name

    def put_data_into_queue(self, buffer, file_id, packet_size=1000):
        logger.debug('Buffer length: %d in downlink %s' % (len(buffer), self.name))
        packets = []
        num_packets = int(np.ceil(len(buffer) / packet_size))
        for i in range(num_packets):
            msg = buffer[(i * packet_size):((i + 1) * packet_size)]
            packet = packet_classes.FilePacket(file_id=file_id, packet_number=i,
                                               total_packet_number=num_packets, payload=msg)
            packets.append(packet)
        packet_length_debug_string = ','.join([str(packet.payload_length) for packet in packets])
        logger.debug('Packet payload lengths: %s for downlink %s' % (packet_length_debug_string, self.name))
        self.packets_to_send += packets

    def send_data(self):
        if not self.packets_to_send:
            logger.debug('No packets to send in downlink %s.' % self.name)
            return
        wait_time = self.prev_packet_size / self.downlink_speed_bytes_per_sec
        if time.time() - self.prev_packet_time > wait_time:
            buffer = self.packets_to_send[0].to_buffer()
            if buffer.find(chr(constants.SYNC_BYTE)):
                raise AttributeError('Start byte found within buffer of downlink %s.' % self.name)

            self.send(buffer, self.downlink_ip, self.downlink_port)
            self.prev_packet_size = len(buffer)
            self.prev_packet_time = time.time()
            self.packets_to_send = self.packets_to_send[1:]

    def send(self, msg, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bytes_sent = sock.sendto(msg, (ip, port))
        logger.debug('Bytes sent on hirate downlink %s: %d' % (self.name, bytes_sent))
        sock.close()

    def has_bandwidth(self):
        return self.enabled and not self.packets_to_send

    def flush_packet_queue(self):
        num_items = len(self.packets_to_send)
        self.packets_to_send = []
        logger.info("Flushed %d packets from downlink %s" % (num_items, self.name))


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
        packed_length = struct.pack('>1B', len(msg))
        msg = self.HEADER + packed_length + msg + self.FOOTER
        self._send(msg)

import time
import socket
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

    def put_data_into_queue(self, buffer, file_id, file_type, packet_size=1000):
        packets = []
        num_packets = np.ceil(len(buffer) / packet_size)
        for i in range(int(num_packets)):
            msg = buffer[(i * packet_size):((i + 1) * packet_size)]
            encoded_msg = cobs_encoding.encode_data(msg, 0xFA)
            packet = packet_classes.HiratePacket(file_id=file_id, file_type=file_type, packet_number=i,
                                                 total_packet_number=num_packets, payload=encoded_msg)
            packets.append(packet)
        self.packets_to_send += packets

    def send_data(self):
        wait_time = self.prev_packet_size / self.downlink_speed
        if time.time() - self.prev_packet_time > wait_time:
            buffer = self.packets_to_send[0].to_buffer()
            self.send(buffer, self.downlink_ip, self.downlink_port)
            self.prev_packet_size = len(buffer)
            self.prev_packet_time = time.time()
            self.packets_to_send = self.packets_to_send[1:]

    def send(self, msg, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg, (ip, port))
        sock.close()

    def has_bandwidth(self):
        if not self.packets_to_send:
            return True
        else:
            return False

    def main_loop(self):
        while True:
            self.run_pyro_tasks()
            if self.packets_to_send:
                self.send_data()
            time.sleep(0.5)

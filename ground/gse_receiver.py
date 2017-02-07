import serial
import os
import socket
import time
import csv
from pmc_camera.communication import packet_classes, file_format_classes, constants

from pmc_camera.utils import log

import logging
import struct

logger = logging.getLogger(__name__)


class GSEReceiver():
    def __init__(self, path, serial_port_or_socket_port='/dev/ttyUSB0', baudrate=115200, loop_interval=1):
        """

        loop_interval specifies the time we wait per byte reading loop.

        For the serial port, we will read up to num_bytes (10000) bytes, which, since we have a much lower
        bandwidth than 10000 bps, means we will read as many bytes as come in loop_interval seconds.

        For the openport, we receive small UDP packets. This means that we will
        accumulate data for loop_interval seconds and then return it.

        The timeout for both ports is set to loop_interval since we will not bottleneck the bandwidth as long as we are
        receiving less than num_bytes bps, we will receive as many bytes as possible in loop_interval.
        This simplifies our loop since there is only one time parameter that determines how long the port remains open.

        Parameters
        ----------
        serial_port_or_socket_port: int or string
            if int, used as datagram socket, if string, used as seral port
        baudrate: int
        loop_interval:int

        """
        if type(serial_port_or_socket_port) is int:
            self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port.bind(('0.0.0.0', serial_port_or_socket_port))
            self.port.settimeout(loop_interval)
        else:
            self.port = serial.Serial(serial_port_or_socket_port, baudrate=baudrate)
            self.port.timeout = loop_interval
        self.files = {}
        self.file_status = {}
        self.hirate_file_packet_remainder = ''
        self.setup_directory(path)
        self.last_gse_remainder = ''
        self.loop_interval = loop_interval
        self.num_bytes_per_read = 10000

    def close(self):
        try:
            self.port.close()
        except Exception:
            pass

    def main_loop(self):
        while True:
            buffer = self.get_next_data()
            if not buffer:
                continue
            with open(self.raw_filename, 'ab+') as f:
                f.write(buffer)

            gse_packets, gse_remainder = self.get_gse_packets_from_buffer(self.last_gse_remainder + buffer)
            self.last_gse_remainder = gse_remainder
            gse_hirate_packets, gse_lowrate_packets = self.separate_gse_packets_by_origin(gse_packets)

            self.write_gse_packet_payloads_to_disk(gse_lowrate_packets)

            hirate_packets = self.get_file_packets_and_remainder_from_gse_packets_hirate_origin(gse_hirate_packets)
            self.gather_files_from_file_packets(hirate_packets)

    def get_next_data(self):
        buffer = ''
        start = time.time()
        while (time.time() - start) < self.loop_interval:
            data = self.port.read(self.num_bytes_per_read)
            buffer += data
        if buffer:
            logger.debug('Received %d bytes from serial port' % len(buffer))
        return buffer

    def get_gse_packets_from_buffer(self, buffer):
        gse_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(packet_classes.GSEPacket.START_BYTE))
            if idx == -1:
                # There's no GSE start byte in the buffer
                remainder = buffer
                break
            try:
                gse_packet = packet_classes.GSEPacket(buffer=buffer[idx:])
                gse_packets.append(gse_packet)
                buffer = buffer[idx + gse_packet.header_length + gse_packet.payload_length + 1:]
                if len(buffer) and buffer[0] != chr(packet_classes.GSEPacket.START_BYTE):
                    idx = buffer.find(chr(packet_classes.GSEPacket.START_BYTE))
                    if idx != -1:
                        idx += 1
                    logger.warning('Bad data: %r' % buffer[0:idx])
            except packet_classes.PacketLengthError:
                # This triggers when there are insufficient bytes to finish a GSEPacket
                remainder = buffer[idx:]
                break
            except packet_classes.PacketChecksumError as e:
                logger.warning(str(e))
                remainder = buffer[idx + 1:]
                break
        return gse_packets, remainder

    def separate_gse_packets_by_origin(self, gse_packets):
        lowrate_gse_packets = []
        hirate_gse_packets = []
        for packet in gse_packets:
            origin = packet.origin & packet_classes.GSEPacket.ORIGIN_BITMASK
            if origin == packet_classes.GSEPacket.LOWRATE_ORIGIN:
                lowrate_gse_packets.append(packet)
            if origin == packet_classes.GSEPacket.HIRATE_ORIGIN:
                hirate_gse_packets.append(packet)
        return hirate_gse_packets, lowrate_gse_packets

    def get_file_packets_from_buffer(self, buffer):
        file_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(packet_classes.GSEPacket.START_BYTE))
            if idx == -1:
                logger.debug('no start byte found')
                remainder = buffer
                break
            try:
                file_packet = packet_classes.FilePacket(buffer=buffer[idx:])
                file_packets.append(file_packet)
                buffer = buffer[idx + file_packet.header_length + file_packet.payload_length + 2:]
            except packet_classes.PacketLengthError as e:
                logger.debug(str(e))
                # This triggers when there are insufficient bytes to finish a GSEPacket.
                # This is common - usually just needs to wait for more data.
                remainder = buffer[idx:]
                break
            except (packet_classes.PacketChecksumError, packet_classes.PacketValidityError) as e:
                logger.warning(str(e))
                try:
                    remainder = buffer[idx + 1:]
                except Exception as e:
                    remainder = ''
                break
        return file_packets, remainder

    def write_file_from_file_packets(self, packets, filename):
        data_buffer = ''
        for packet in packets:
            data_buffer += packet.payload

        file_class = file_format_classes.decode_file_from_buffer(data_buffer)

        file_extension = ''
        if file_class.file_type == 1:
            file_extension = '.jpg'
        if file_class.file_type == 5:
            file_extension = '.json'
        if file_class.file_type == 6:
            file_extension = '.json'

        file_class.write_payload_to_file(filename + file_extension)

        with open(self.file_index_filename, 'a') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(
                [time.time(), (filename + file_extension), file_class.file_type, packets[0].file_id, len(data_buffer)])


            # Write file_index csv that updates whenever a new file is written saying what is in the file
            # (file type, size, time, can I get % done?)

    def setup_directory(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        logs_path = os.path.join(path, 'logs')
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)
        self.file_path = os.path.join(path, 'files')
        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)
        self.raw_filename = os.path.join(logs_path, 'raw.log')
        self.lowrate_filename = os.path.join(logs_path, 'lowrate.log')
        self.packet_index_filename = os.path.join(path, 'packet_index.csv')
        self.file_index_filename = os.path.join(path, 'file_index.csv')

        with open(self.packet_index_filename, 'w') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(['epoch', 'current_file_id', 'packet_number', 'total_packets'])

        with open(self.file_index_filename, 'a') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(['epoch', 'filename', 'file_type', 'file_id', 'file_size'])

    def write_gse_packet_payloads_to_disk(self, gse_lowrate_packets):
        f = open(self.lowrate_filename, 'ab+')
        for packet in gse_lowrate_packets:
            f.write(packet.to_buffer() + '\n')
        f.close()

    def get_file_packets_and_remainder_from_gse_packets_hirate_origin(self, gse_hirate_packets):
        gse_hirate_buffer = ''
        for packet in gse_hirate_packets:
            gse_hirate_buffer += packet.payload
        file_packets, remainder = self.get_file_packets_from_buffer(
            self.hirate_file_packet_remainder + gse_hirate_buffer)
        for packet in file_packets:
            logger.debug('File_id: %d, Packet Number: %d of %d' % (
                packet.file_id, packet.packet_number, packet.total_packet_number))
            logger.debug('Packet length: %d' % packet.payload_length)
        self.hirate_file_packet_remainder = remainder
        return file_packets

    def gather_files_from_file_packets(self, file_packets):
        for packet in file_packets:
            if packet.file_id in self.files.keys():
                self.files[packet.file_id].append(packet)
            else:
                self.files[packet.file_id] = [packet]

            if not self.file_status.has_key(packet.file_id):
                self.file_status[packet.file_id] = {'first_timestamp': time.time(),
                                                    'recent_timestamp': time.time(),
                                                    'packets_received': [packet.packet_number],
                                                    'packets_expected': packet.total_packet_number,
                                                    'first_packet': packet}
            else:
                self.file_status[packet.file_id]['recent_timestamp'] = time.time()
                self.file_status[packet.file_id]['packets_received'].append(packet.packet_number)

            with open(self.packet_index_filename, 'a') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
                writer.writerow([time.time(), packet.file_id, packet.packet_number, packet.total_packet_number])

        for file_id in self.files.keys():
            sorted_packets = sorted(self.files[file_id], key=lambda k: k.packet_number)
            if [packet.packet_number for packet in sorted_packets] == range(sorted_packets[0].total_packet_number):
                logger.info('Full file received: file id %d' % file_id)
                new_filename = '%d' % file_id
                new_filename = os.path.join(self.file_path, new_filename)
                self.write_file_from_file_packets(sorted_packets, new_filename)
                del self.files[file_id]

    def get_files_status(self):
        return self.file_status


if __name__ == "__main__":
    log.setup_file_handler()
    log.setup_stream_handler(level=logging.DEBUG)
    path = os.path.join('/home/pmc/pmchome/gse_receiver_data', time.strftime('%Y-%m-%d_%H-%M-%S'))
    g = GSEReceiver(path=path)
    g.main_loop()

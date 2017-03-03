import csv
import logging
import os
import socket
import threading
import time

import errno
import serial
from pmc_turbo.communication import packet_classes

from pmc_turbo.communication import file_format_classes


class GSEReceiver():
    GSE_SERIAL = 'gse-serial'
    OPENPORT_SOCKET = 'openport-socket'

    def __init__(self, root_path, serial_port_or_socket_port, baudrate, loop_interval, use_gse_packets, name):
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
        self.name = name
        self.root_path = root_path
        self.logger = logging.getLogger('pmc_turbo.'+name)
        self.use_gse_packets = use_gse_packets
        if type(serial_port_or_socket_port) is int:
            self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port.bind(('0.0.0.0', serial_port_or_socket_port))
            self.port.settimeout(loop_interval)
            self.socket_type = self.OPENPORT_SOCKET
        else:
            self.port = serial.Serial(serial_port_or_socket_port, baudrate=baudrate)
            self.port.timeout = loop_interval
            self.socket_type = self.GSE_SERIAL
        self.files = {}
        self.file_status = {}
        self.file_packet_remainder = ''
        self.setup_directory()
        self.last_gse_remainder = ''
        self.loop_interval = loop_interval
        self.num_bytes_per_read = 10000
        self._exit = False

    def close(self):
        self._exit = True
        self.thread.join(2)
        try:
            self.port.close()
        except Exception:
            pass

    def start_main_loop_thread(self):
        self.thread = threading.Thread(target=self.main_loop)
        self.thread.daemon = True
        self.thread.start()

    def main_loop(self):
        while not self._exit:
            buffer = self.get_next_data()
            if not buffer:
                self.logger.debug('Waiting for data')
                continue
            with open(self.raw_filename, 'ab+') as f:
                f.write(buffer)

            if self.use_gse_packets:
                gse_packets, gse_remainder = packet_classes.get_packets_from_buffer(self.last_gse_remainder + buffer,
                                                                                    packet_class=packet_classes.GSEPacket,
                                                                                    start_byte=packet_classes.GSEPacket.START_BYTE)
                self.last_gse_remainder = gse_remainder
                gse_hirate_packets, gse_lowrate_packets = packet_classes.separate_gse_packets_by_origin(gse_packets)

                self.write_gse_packet_payloads_to_disk(gse_lowrate_packets)

                file_packet_buffer = ''
                for packet in gse_hirate_packets:
                    file_packet_buffer += packet.payload

            else:
                file_packet_buffer = buffer

            file_packets, remainder = packet_classes.get_packets_from_buffer(self.file_packet_remainder + file_packet_buffer,
                                                                             packet_class=packet_classes.FilePacket,
                                                                             start_byte=packet_classes.FilePacket._valid_start_byte)
            for packet in file_packets:
                self.logger.debug('File_id: %d, Packet Number: %d of %d, length %d' % (
                    packet.file_id, packet.packet_number, packet.total_packet_number, packet.payload_length))
            self.file_packet_remainder = remainder

            self.gather_files_from_file_packets(file_packets)

    def get_next_data(self):
        buffer = ''
        start = time.time()
        while (time.time() - start) < self.loop_interval:
            data = ''
            if self.socket_type == self.OPENPORT_SOCKET:
                try:
                    data = self.port.recv(self.num_bytes_per_read)
                except socket.timeout:
                    time.sleep(0.01)
                    self.logger.debug('Timeout')
                    pass
            else:
                data = self.port.read(self.num_bytes_per_read)
            buffer += data
        if buffer:
            self.logger.debug('Received %d bytes from %s' % (len(buffer),self.name))
        return buffer


    def assemble_file_from_packets(self, packets):
        data_buffer = ''.join([packet.payload for packet in packets])
        return file_format_classes.decode_file_from_buffer(data_buffer)

    def write_file(self, file_class, file_id):
        file_status = self.file_status[file_id]
        base_filename = time.strftime('%Y-%m-%d_%H%M%S') + ('_%06d' % file_id)
        file_class.write_payload_to_file(os.path.join(self.payload_path,base_filename))
        filename = os.path.join(self.file_path,base_filename)
        file_class.write_buffer_to_file(filename)
        source_path = os.path.join(self.by_source_path,('camera-%d' % file_class.camera_id))
        try:
            os.makedirs(source_path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(source_path):
                pass
            else:
                self.logger.exception("Could not create %s" % source_path)
        os.symlink(filename,os.path.join(source_path,base_filename))

        try:
            frame_timestamp_ns = file_class.frame_timestamp_ns
        except AttributeError:
            frame_timestamp_ns = -1

        with open(self.file_index_filename, 'a') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(
                [file_id, file_status['first_timestamp'],file_status['recent_timestamp'], time.time(), filename,
                 file_class.file_type,file_class.request_id, file_class.camera_id, frame_timestamp_ns,

                len(file_status['packets_received']), file_status['packets_expected'] ])

    def setup_directory(self):
        path = os.path.join(self.root_path,self.name)
        if not os.path.exists(path):
            os.makedirs(path)
        logs_path = os.path.join(path, 'logs')
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)
        self.file_path = os.path.join(path, 'files')
        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)
        self.payload_path = os.path.join(path,'payloads')
        if not os.path.exists(self.payload_path):
            os.makedirs(self.payload_path)

        self.by_source_path = os.path.join(self.root_path,'by-source')

        self.raw_filename = os.path.join(logs_path, 'raw.log')
        self.lowrate_filename = os.path.join(logs_path, 'lowrate.log')
        self.packet_index_filename = os.path.join(path, 'packet_index.csv')
        self.file_index_filename = os.path.join(path, 'file_index.csv')

        with open(self.packet_index_filename, 'w') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(['epoch', 'current_file_id', 'packet_number', 'total_packets'])

        with open(self.file_index_filename, 'a') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE, lineterminator='\n')
            writer.writerow(['file_id','first_timestamp', 'last_timestamp', 'file_write_timestamp', 'filename',
                             'file_type','request_id', 'camera_id', 'frame_timestamp_ns',
                             'packets_received', 'packets_expected'])

    def write_gse_packet_payloads_to_disk(self, gse_lowrate_packets):
        f = open(self.lowrate_filename, 'ab+')
        for packet in gse_lowrate_packets:
            f.write(packet.to_buffer() + '\n')
        f.close()

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
                self.logger.info('Full file received: file id %d' % file_id)
                try:
                    file_class = self.assemble_file_from_packets(sorted_packets)
                except RuntimeError:
                    self.logger.exception("Failed to assemble file id %d" % file_id)
                    continue
                self.write_file(file_class,file_id=file_id)
                del self.files[file_id]

    def get_files_status(self):
        return self.file_status

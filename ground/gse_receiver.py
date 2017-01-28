import serial
import os
import socket
import time
from pmc_camera.communication import packet_classes, file_format_classes, constants

import logging
import struct

logger = logging.getLogger(__name__)


class GSEReceiver():
    def __init__(self, serial_port_or_socket_port='/dev/ttyUSB0', baudrate=115200, timeout=1):
        '''

        Parameters
        ----------
        serial_port_or_socket_port: int or string
            if int, used as datagram socket, if string, used as seral port
        baudrate: int
        timeout:int


        '''
        if type(serial_port_or_socket_port) is int:
            self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port.bind(('0.0.0.0', serial_port_or_socket_port))
            self.port.settimeout(timeout)
        else:
            self.port = serial.Serial(serial_port_or_socket_port, baudrate=baudrate)
            self.port.timeout = timeout
        self.files = {}
        self.hirate_remainder = ''
        return

    def close(self):
        try:
            self.port.close()
        except Exception:
            pass

    def get_new_data_into_buffer(self, time_loop):
        buffer = ''
        start = time.time()
        while (time.time() - start) < time_loop:
            data = self.port.read(10000)
            buffer += data
        if buffer:
            logger.debug('Received %d bytes from serial port' % len(buffer))
        return buffer

    def get_gse_packets_from_buffer(self, buffer):
        gse_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(constants.SYNC_BYTE))
            if idx == -1:
                # There's no GSE start byte in the buffer
                remainder = buffer
                break
            try:
                gse_packet = packet_classes.GSEPacket(buffer=buffer[idx:], greedy=False)
                gse_packets.append(gse_packet)
                # print '%r' % buffer[idx + gse_packet._header_length + gse_packet.payload_length + 1:]
                buffer = buffer[idx + gse_packet.header_length + gse_packet.payload_length + 1:]
                if len(buffer) and buffer[0] != chr(constants.SYNC_BYTE):
                    idx = buffer.find(chr(constants.SYNC_BYTE))
                    if idx != -1:
                        idx += 1
                    logger.warning('Bad data: %r' % buffer[0:idx])
            except packet_classes.PacketLengthError:
                # This triggers when there are insufficient bytes to finish a GSEPacket
                remainder = buffer[idx:]
                break
            except packet_classes.PacketChecksumError as e:
                logger.debug(str(e))
                remainder = buffer[idx + 1:]
                break
        return gse_packets, remainder

    def separate_gse_packets_by_origin(self, gse_packets):
        lowrate_gse_packets = [packet for packet in gse_packets if packet.origin == 1]
        hirate_gse_packets = [packet for packet in gse_packets if packet.origin == 2]
        return hirate_gse_packets, lowrate_gse_packets

    def get_hirate_packets_from_buffer(self, buffer):
        hirate_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(constants.SYNC_BYTE))
            if idx == -1:
                logger.debug('no start byte found')
                remainder = buffer
                break
            try:
                hirate_packet = packet_classes.HiratePacket(buffer=buffer[idx:])
                hirate_packets.append(hirate_packet)
                buffer = buffer[idx + hirate_packet.header_length + hirate_packet.payload_length + 2:]
            except packet_classes.PacketLengthError as e:
                logger.debug(str(e))
                # This triggers when there are insufficient bytes to finish a GSEPacket.
                # This is common - usually just needs to wait for more data.
                remainder = buffer[idx:]
                break
            except packet_classes.PacketChecksumError as e:
                logger.warning(str(e))
                # This comes up occasionally - i need to think about how to handle this
                # Probably just toss the packet... which is what I do already.
                # remainder = buffer[idx + 6 + 1000 + 2:]
                remainder = buffer[idx + 1:]
                # This is hardcoded right now because I know these lengths... I need to fix this in the future
                # The problem is I can't use hirate_packet.payload_length, etc. since the packet never gets formed
                # It raises this exception instead - possible to pass arguments in exception?
                break
            except packet_classes.PacketValidityError as e:
                logger.warning(str(e))
                remainder = buffer[idx + 1:]
                break
        return hirate_packets, remainder

    def write_file_from_hirate_packets(self, packets, filename):
        data_buffer = ''
        data_buffer = ''
        for packet in packets:
            data_buffer += packet.payload

        file_class = file_format_classes.decode_file_from_buffer(data_buffer)
        file_class.write_buffer_to_file(filename + '_buffer')

    def log_lowrate_status(self, packet):
        # Problem: currently communicator aggregates lots of statuses to send down, then sends all... think about this
        # It is sure to create errors and my fix here is just a hack right now
        # logger.debug('%r' % packet.payload)\
        format_string = '>1B1L1L1H1H1L'
        overall_status, frame_status, frame_id, focus_step, aperture_stop, exposure_ms = struct.unpack(
            format_string,
            packet.payload[:struct.calcsize(format_string)])
        logger.info(
            'Overall status: %d \n Frame status: %d \n Frame id: %d \n Focus Step: %d \n Aperture stop: %d \n Exposure: %d' % (
                overall_status, frame_status, frame_id, focus_step, aperture_stop, exposure_ms))

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

    def dump_raw_bytes_to_file(self, buffer):
        f = open(self.raw_filename, 'ab+')
        f.write(buffer)
        f.close()

    def write_gse_packet_payloads_to_disk(self, gse_lowrate_packets):
        f = open(self.lowrate_filename, 'ab+')
        for packet in gse_lowrate_packets:
            f.write(packet.to_buffer() + '\n')
            self.log_lowrate_status(packet)
        f.close()

    def get_hirate_packets_and_remainder_from_gse_packets_and_remainder(self, gse_hirate_packets):
        gse_hirate_buffer = ''
        for packet in gse_hirate_packets:
            gse_hirate_buffer += packet.payload
        hirate_packets, remainder = g.get_hirate_packets_from_buffer(self.hirate_remainder + gse_hirate_buffer)
        for packet in hirate_packets:
            logger.debug('File_id: %d, Packet Number: %d of %d' % (
                packet.file_id, packet.packet_number, packet.total_packet_number))
            logger.debug('Packet length: %d' % packet.payload_length)
        self.hirate_remainder = remainder
        return hirate_packets

    def gather_files_from_hirate_packets(self, hirate_packets):
        for packet in hirate_packets:
            if packet.file_id in self.files.keys():
                self.files[packet.file_id].append(packet)
            else:
                self.files[packet.file_id] = [packet]

        for file_id in self.files.keys():
            sorted_packets = sorted(self.files[file_id], key=lambda k: k.packet_number)
            if [packet.packet_number for packet in sorted_packets] == range(sorted_packets[0].total_packet_number):
                logger.debug('Full image received: file id %d' % file_id)
                jpg_filename = '%d' % file_id
                jpg_filename = os.path.join(self.file_path, jpg_filename)
                g.write_file_from_hirate_packets(sorted_packets, jpg_filename)
                del self.files[file_id]

    def run(self):
        path = '/home/pmc/gse_receiver_data'
        path = os.path.join(path, time.strftime('%Y-%m-%d'))
        self.setup_directory(path)

        self.main_loop()

    def main_loop(self):
        while True:
            buffer = g.get_new_data_into_buffer(1)
            if not buffer:
                continue
            self.dump_raw_bytes_to_file(buffer)

            gse_packets, gse_remainder = g.get_gse_packets_from_buffer(buffer)
            gse_hirate_packets, gse_lowrate_packets = g.separate_gse_packets_by_origin(gse_packets)

            self.write_gse_packet_payloads_to_disk(gse_lowrate_packets)

            hirate_packets = self.get_hirate_packets_and_remainder_from_gse_packets_and_remainder(gse_hirate_packets)
            self.gather_files_from_hirate_packets(hirate_packets)


if __name__ == "__main__":
    # IPython.embed()

    logger = logging.getLogger('ground')
    default_handler = logging.StreamHandler()

    LOG_DIR = '/home/pmc/logs/gse_receiver'
    filename = os.path.join(LOG_DIR, (time.strftime('%Y-%m-%d_%H%M%S.txt')))
    default_filehandler = logging.FileHandler(filename=filename)

    message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
    default_formatter = logging.Formatter(message_format)
    default_handler.setFormatter(default_formatter)
    default_filehandler.setFormatter(default_formatter)
    logger.addHandler(default_handler)
    logger.addHandler(default_filehandler)
    logger.setLevel(logging.DEBUG)

    g = GSEReceiver()
    g.run()

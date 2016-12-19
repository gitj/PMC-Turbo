import serial
import os
import time
from pmc_camera.communication.hirate import cobs_encoding
from pmc_camera.communication import packet_classes
import cv2
import matplotlib.pyplot
import IPython
import logging
import struct

logger = logging.getLogger(__name__)


class GSEReceiver():
    def __init__(self):
        return

    def get_new_data_into_buffer(self, time_loop, usb_port_address='/dev/ttyUSB0', baudrate=115200):
        buffer = ''
        ser = serial.Serial(usb_port_address, baudrate=baudrate)
        ser.timeout = 1
        start = time.time()
        while (time.time() - start) < time_loop:
            data = ser.read(10000)
            buffer += data
        ser.close()
        return buffer

    def get_gse_packets_from_buffer(self, buffer):
        gse_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(0xFA))
            if idx == -1:
                # There's no GSE start byte in the buffer
                remainder = buffer
                break
            try:
                gse_packet = packet_classes.GSEPacket(buffer=buffer[idx:], greedy=False)
                gse_packets.append(gse_packet)
                # print '%r' % buffer[idx + gse_packet._header_length + gse_packet.payload_length + 1:]
                buffer = buffer[idx + gse_packet._header_length + gse_packet.payload_length + 1:]
            except packet_classes.PacketLengthError:
                # This triggers when there are insufficient bytes to finish a GSEPacket
                remainder = buffer[idx:]
                break
        return gse_packets, remainder

    def separate_hirate_and_lowrate_gse_packets(self, gse_packets):
        lowrate_gse_packets = [packet for packet in gse_packets if packet.origin == 1]
        hirate_gse_packets = [packet for packet in gse_packets if packet.origin == 2]
        return hirate_gse_packets, lowrate_gse_packets

    def get_hirate_packets_from_buffer(self, buffer):
        hirate_packets = []
        remainder = ''
        while buffer:
            idx = buffer.find(chr(0xFA))
            if idx == -1:
                logger.debug('no start byte found')
                remainder = buffer
                break
            try:
                hirate_packet = packet_classes.HiratePacket(buffer=buffer[idx:])
                hirate_packets.append(hirate_packet)
                buffer = buffer[idx + hirate_packet._header_length + hirate_packet.payload_length + 2:]
            except packet_classes.PacketLengthError as e:
                logger.debug(str(e))
                # This triggers when there are insufficient bytes to finish a GSEPacket.
                # This is common - usually just needs to wait for more data.
                remainder = buffer[idx:]
                break
            except packet_classes.PacketChecksumError as e:
                logger.debug(str(e))
                # This comes up occasionally - i need to think about how to handle this
                # Probably just toss the packet... which is what I do already.
                # remainder = buffer[idx + 6 + 1000 + 2:]
                remainder = buffer[idx + 6:]
                # This is hardcoded right now because I know these lengths... I need to fix this in the future
                # The problem is I can't use hirate_packet.payload_length, etc. since the packet never gets formed
                # It raises this exception instead - possible to pass arguments in exception?
                break
        return hirate_packets, remainder

    def write_file_from_hirate_packets(self, packets, filename):
        data_buffer = ''
        for packet in packets:
            data_buffer += cobs_encoding.decode_data(packet.payload, 0xFA)
        # data_buffer = cobs_encoding.decode_data(data_buffer, 0xFA)
        with open(filename, 'wb') as f:
            f.write(data_buffer)
            # img = cv2.imread(filename)
            # matplotlib.pyplot.imshow(img)

    def log_lowrate_status(self, packet):
        # Problem: currently communicator aggregates lots of statuses to send down, then sends all... think about this
        # It is sure to create errors and my fix here is just a hack right now
        # logger.debug('%r' % packet.payload)\
        format_string = '>1B1L1L1H1H1L'
        overall_status, frame_status, frame_id, focus_step, aperture_stop, exposure_ms = struct.unpack(
            format_string,
            packet.payload[-struct.calcsize(format_string):])
        logger.info(
            'Overall status: %d \n Frame status: %d \n Frame id: %d \n Focus Step: %d \n Aperture stop: %d \n Exposure: %d' % (
                overall_status, frame_status, frame_id, focus_step, aperture_stop, exposure_ms))

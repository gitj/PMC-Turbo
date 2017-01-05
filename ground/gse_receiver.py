import serial
import os
import time
from pmc_camera.communication.hirate import cobs_encoding
from pmc_camera.communication import packet_classes, file_format_classes

import logging
import struct

logger = logging.getLogger(__name__)


class GSEReceiver():
    # Class for GSEReceiver
    def __init__(self, usb_port_address='/dev/ttyUSB0', baudrate=115200):
        self.ser = serial.Serial(usb_port_address, baudrate=baudrate)
        self.ser.timeout = 1
        return

    def __del__(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def get_new_data_into_buffer(self, time_loop):
        buffer = ''
        start = time.time()
        while (time.time() - start) < time_loop:
            data = self.ser.read(10000)
            buffer += data
        if buffer:
            logger.debug('Received %d bytes from serial port' % len(buffer))
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
                buffer = buffer[idx + gse_packet.header_length + gse_packet.payload_length + 1:]
                if len(buffer) and buffer[0] != chr(0xFA):
                    idx = buffer.find(chr(0xFA))
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
        return hirate_packets, remainder

    def write_file_from_hirate_packets(self, packets, filename, file_type):
        data_buffer = ''
        for packet in packets:
            data_buffer += cobs_encoding.decode_data(packet.payload, 0xFA)
        if file_type == 1:
            jpeg_file_class = file_format_classes.JPEGFile(buffer=data_buffer)
            jpeg_file_class.write(filename)
            #img = cv2.imread(filename + '.jpg')
            #self.ax.cla()
            #self.ax.imshow(img)
            #self.ax.set_title(filename)
            #self.fig.canvas.draw()
        else:
            with open(filename, 'wb') as f:
                f.write(data_buffer)

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

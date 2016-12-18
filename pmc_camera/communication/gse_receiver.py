import serial
import os
import time
import constants
from hirate import cobs_encoding
import packet_classes
import cv2
import matplotlib.pyplot
import IPython
import logging


# logger = logging.getLogger(__name__)


def get_new_data_into_buffer(time_loop, usb_port_address='/dev/ttyUSB0', baudrate=115200):
    buffer = ''
    ser = serial.Serial(usb_port_address, baudrate=baudrate)
    ser.timeout = 1
    start = time.time()
    while (time.time() - start) < time_loop:
        data = ser.read(10000)
        buffer += data
    ser.close()
    return buffer


def get_gse_packets_from_buffer(buffer):
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


def separate_hirate_and_lowrate_gse_packets(gse_packets):
    lowrate_gse_packets = [packet for packet in gse_packets if packet.origin == 1]
    hirate_gse_packets = [packet for packet in gse_packets if packet.origin == 2]
    return hirate_gse_packets, lowrate_gse_packets


def get_hirate_packets_from_buffer(buffer):
    hirate_packets = []
    remainder = ''
    while buffer:
        idx = buffer.find(chr(0x17))
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
            remainder = buffer[idx + 6 + 1000 + 2:]
            # This is hardcoded right now because I know these lengths... I need to fix this in the future
            # The problem is I can't use hirate_packet.payload_length, etc. since the packet never gets formed
            # It raises this exception instead - possible to pass arguments in exception?
            break
    return hirate_packets, remainder


def write_file_from_hirate_packets(packets, filename):
    data_buffer = ''
    for packet in packets:
        data_buffer += packet.payload
    data_buffer = cobs_encoding.decode_data(data_buffer, 0x17)
    with open(filename, 'wb') as f:
        f.write(data_buffer)
        # img = cv2.imread(filename)
        # matplotlib.pyplot.imshow(img)


def main():
    timestamp = time.strftime('%Y-%m-%d_%H%M%S')
    generic_path = './gse_receiver_data'
    path = os.path.join(generic_path, timestamp)
    if not os.path.exists(path):
        os.makedirs(path)
    raw_filename = os.path.join(path, 'raw.log')
    lowrate_file_name = os.path.join(path, 'lowrate.log')

    files = {}
    hirate_remainder = ''

    while True:
        buffer = get_new_data_into_buffer(1)
        if not buffer:
            continue
        f = open(raw_filename, 'ab+')
        f.write(buffer)
        f.close()

        gse_packets, gse_remainder = get_gse_packets_from_buffer(buffer)
        gse_hirate_packets, gse_lowrate_packets = separate_hirate_and_lowrate_gse_packets(gse_packets)

        f = open(raw_filename, 'ab+')
        for packet in gse_lowrate_packets:
            # f.write(packet.to_buffer())
            logger.debug('lowrate_received')
        f.close()

        gse_hirate_buffer = ''
        for packet in gse_hirate_packets:
            gse_hirate_buffer += packet.payload
        hirate_packets, remainder = get_hirate_packets_from_buffer(hirate_remainder + gse_hirate_buffer)
        for packet in hirate_packets:
            logger.debug('File_id: %d, Packet Number: %d or %d' % (
            packet.file_id, packet.packet_number, packet.total_packet_number))
        hirate_remainder = remainder

        for packet in hirate_packets:
            if packet.file_id in files.keys():
                files[packet.file_id].append(packet)
            else:
                files[packet.file_id] = [packet]

        for file_id in files.keys():
            sorted_packets = sorted(files[file_id], key=lambda k: k.packet_number)
            if [packet.packet_number for packet in sorted_packets] == range(sorted_packets[0].total_packet_number):
                logger.debug('Full image received: file id %d' % file_id)
                jpg_filename = '%d.jpg' % file_id
                jpg_filename = os.path.join(path, jpg_filename)
                write_file_from_hirate_packets(sorted_packets, jpg_filename)
                del files[file_id]


if __name__ == "__main__":
    # IPython.embed()

    logger = logging.getLogger('pmc_camera')
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

    main()

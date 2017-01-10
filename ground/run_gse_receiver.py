import os
import time
import logging
from ground import gse_receiver


# Runs gse_receiver.GSEReceiver

def main():
    g = gse_receiver.GSEReceiver()
    timestamp = time.strftime('%Y-%m-%d_%H%M%S')
    generic_path = './gse_receiver_data'
    path = os.path.join(generic_path, timestamp)
    if not os.path.exists(path):
        os.makedirs(path)
    logs_path = os.path.join(path, 'logs')
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    image_path = os.path.join(path, 'images')
    if not os.path.exists(image_path):
        os.makedirs(image_path)
    raw_filename = os.path.join(logs_path, 'raw.log')
    lowrate_filename = os.path.join(logs_path, 'lowrate.log')

    files = {}
    hirate_remainder = ''

    while True:
        buffer = g.get_new_data_into_buffer(1)
        if not buffer:
            continue
        f = open(raw_filename, 'ab+')
        f.write(buffer)
        f.close()

        gse_packets, gse_remainder = g.get_gse_packets_from_buffer(buffer)
        gse_hirate_packets, gse_lowrate_packets = g.separate_hirate_and_lowrate_gse_packets(gse_packets)

        f = open(lowrate_filename, 'ab+')
        for packet in gse_lowrate_packets:
            f.write(packet.to_buffer() + '\n')
            # logger.debug('lowrate_received')
            g.log_lowrate_status(packet)
        f.close()

        gse_hirate_buffer = ''
        for packet in gse_hirate_packets:
            gse_hirate_buffer += packet.payload
        hirate_packets, remainder = g.get_hirate_packets_from_buffer(hirate_remainder + gse_hirate_buffer)
        for packet in hirate_packets:
            logger.debug('File_id: %d, Packet Number: %d of %d' % (
                packet.file_id, packet.packet_number, packet.total_packet_number))
            logger.debug('Packet length: %d' % packet.payload_length)
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
                jpg_filename = '%d' % file_id
                jpg_filename = os.path.join(image_path, jpg_filename)
                g.write_file_from_hirate_packets(sorted_packets, jpg_filename)
                del files[file_id]


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

    main()

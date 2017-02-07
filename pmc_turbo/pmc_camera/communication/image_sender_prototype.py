from __future__ import division

import time

import Pyro4

import constants
from hirate import hirate_sending_methods, cobs_encoding

PACKET_SIZE = 1000
DOWNLINK_BYTES_PER_SEC = 500
START_BYTE = constants.TEST_START_BYTE
IP, PORT = '192.168.1.54', 4002


def main():
    Pyro4.config.SERIALIZER = 'pickle'
    server = Pyro4.Proxy('PYRO:image@192.168.1.30:50001')
    packets_to_send = []
    file_id = 55
    wait_time = PACKET_SIZE / DOWNLINK_BYTES_PER_SEC
    while True:
        if not packets_to_send:
            image, metadata = server.get_latest_jpeg()
            file_id += 1
            encoded_image = cobs_encoding.encode_data(image, escape_character=START_BYTE)
            print len(encoded_image)
            packets_to_send = hirate_sending_methods.data_to_hirate_packets(PACKET_SIZE, START_BYTE, file_id,
                                                                            encoded_image)
        hirate_sending_methods.send(packets_to_send[0].to_buffer(), IP, PORT)
        packets_to_send = packets_to_send[1:]
        time.sleep(wait_time)


if __name__ == "__main__":
    main()

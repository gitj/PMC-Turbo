import unittest
import numpy as np
import struct
import random
from pmc_camera.communication import constants
from pmc_camera.communication.hirate import hirate_sending_methods, hirate_receiving_methods, cobs_encoding


class HirateTests(unittest.TestCase):
    def setUp(self):
        np.random.seed(0)
        self.random_msg = np.random.randint(0, 255, size=10000).astype('uint8')
        return

    def tearDown(self):
        return

    def good_buffer_test(self):
        encoded_data = cobs_encoding.encode_data(self.random_msg, escape_character=constants.SYNC_BYTE)
        chunks = hirate_sending_methods.chunk_data_by_size(chunk_size=1000, start_byte=constants.SYNC_BYTE, file_id=0,
                                                           data=encoded_data)
        buffer = ''
        for chunk in chunks:
            buffer += chunk
        packets = hirate_receiving_methods.get_packets_from_buffer(buffer, start_byte=chr(constants.SYNC_BYTE))
        files = hirate_receiving_methods.packets_to_files(packets)
        decoded_data = cobs_encoding.decode_data(files[0], escape_character=constants.SYNC_BYTE)
        unpacked_data = struct.unpack(('%dB' % len(decoded_data)), decoded_data)
        unpacked_data_array = np.array(unpacked_data).astype('uint8')
        assert (np.array_equal(self.random_msg, unpacked_data_array) == True)

    def two_files_shuffled_together_test(self):
        encoded_data = cobs_encoding.encode_data(self.random_msg, escape_character=constants.SYNC_BYTE)
        chunks0 = hirate_sending_methods.chunk_data_by_size(chunk_size=1000, start_byte=constants.SYNC_BYTE, file_id=0,
                                                            data=encoded_data)
        chunks1 = hirate_sending_methods.chunk_data_by_size(chunk_size=1000, start_byte=constants.SYNC_BYTE, file_id=1,
                                                            data=encoded_data)
        chunks = chunks0 + chunks1
        random.seed(0)
        random.shuffle(chunks)
        buffer = ''
        for chunk in chunks:
            buffer += chunk
        packets = hirate_receiving_methods.get_packets_from_buffer(buffer, start_byte=chr(constants.SYNC_BYTE))
        files = hirate_receiving_methods.packets_to_files(packets)

        decoded_data0 = cobs_encoding.decode_data(files[0], escape_character=constants.SYNC_BYTE)
        unpacked_data0 = struct.unpack(('%dB' % len(decoded_data0)), decoded_data0)
        unpacked_data_array0 = np.array(unpacked_data0).astype('uint8')
        assert (np.array_equal(self.random_msg, unpacked_data_array0) == True)

        decoded_data1 = cobs_encoding.decode_data(files[1], escape_character=constants.SYNC_BYTE)
        unpacked_data1 = struct.unpack(('%dB' % len(decoded_data1)), decoded_data1)
        unpacked_data_array1 = np.array(unpacked_data1).astype('uint8')
        assert (np.array_equal(self.random_msg, unpacked_data_array1) == True)

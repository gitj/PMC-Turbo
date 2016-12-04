import cobs.cobs
import unittest
import numpy as np
import struct

def encode_data(data):
    a = cobs.cobs.encode(data)
    b = a.replace('\x10', '\x00')
    c = cobs.cobs.encode(b)
    d = c.replace('\x10', '\x00')
    return d

def decode_data(data):
    e = data.replace('\x00', '\x10')
    f = cobs.cobs.decode(e)
    g = f.replace('\x00', '\x10')
    h = cobs.cobs.decode(g)
    return h

class CobsTests(unittest.TestCase):
    def setUp(self):
        return

    def tearDown(self):
        return

    def test_null_case(self):
        buffer = '\x10\x14\x06\x11\x11\x11\x11\x11\x11\x03'
        data = buffer[1:]
        encoded_data = encode_data(data)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == data)

    def test_all_zeros(self):
        buffer = '\x10\x14\x06\x00\x00\x00\x00\x00\x00\x03'
        data = buffer[1:]
        encoded_data = encode_data(data)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == data)

    def test_one_10(self):
        buffer =  '\x10\x14\x06\x11\x11\x10\x11\x11\x11\x03'
        data = buffer[1:]
        encoded_data = encode_data(data)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == data)

    def test_all_10(self):
        buffer =  '\x10\x14\x06\x10\x10\x10\x10\x10\x10\x03'
        data = buffer[1:]
        encoded_data = encode_data(data)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == data)

    def test_alternating_0_and_10(self):
        buffer =  '\x10\x14\x06\x00\x10\x00\x10\x00\x10\x03'
        data = buffer[1:]
        encoded_data = encode_data(data)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == data)

    def test_random_data(self):
        np.random.seed(0)
        random_msg = np.random.randint(0, 255, size=10000).astype('uint8')
        format_string = '%dB' % len(random_msg)
        packet = struct.pack(format_string, *random_msg)
        encoded_data = encode_data(packet)
        assert(encoded_data.find('\x10') == -1)
        decoded_data = decode_data(encoded_data)
        assert(decoded_data == packet)
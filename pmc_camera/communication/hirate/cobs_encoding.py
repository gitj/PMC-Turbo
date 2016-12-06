import cobs.cobs
import numpy as np

def encode_data(data):
    a = cobs.cobs.encode(data)
    b = np.bitwise_xor(np.fromstring(a,dtype='uint8'),0x10).tostring()
    return b

def decode_data(data):
    c = np.bitwise_xor(np.fromstring(data,dtype='uint8'),0x10).tostring()
    d = cobs.cobs.decode(c)
    return d
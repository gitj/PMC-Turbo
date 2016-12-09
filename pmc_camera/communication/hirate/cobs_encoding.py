import cobs.cobs
import numpy as np
from pmc_camera.communication import constants


def encode_data(data, escape_character=constants.SIP_START_BYTE):
    a = cobs.cobs.encode(data)
    b = np.bitwise_xor(np.fromstring(a, dtype='uint8'), escape_character).tostring()
    return b


def decode_data(data, escape_character=constants.SIP_START_BYTE):
    c = np.bitwise_xor(np.fromstring(data, dtype='uint8'), escape_character).tostring()
    d = cobs.cobs.decode(c)
    return d
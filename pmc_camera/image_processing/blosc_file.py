import numpy as np
import blosc
from pmc_camera.pycamera import dtypes

import logging
logger = logging.getLogger(__name__)

def load_blosc_file(filename):
    logger.debug("Reading blosc file from %s" % filename)
    with open(filename, 'rb') as fh:
        data = blosc.decompress(fh.read())
    return data

def load_blosc_image(filename):
    data = load_blosc_file(filename)
    image = np.frombuffer(data[:-dtypes.chunk_num_bytes],dtype='uint16')
    image.shape = dtypes.image_dimensions
    chunk_data = np.frombuffer(data[-dtypes.chunk_num_bytes:],dtype=dtypes.chunk_dtype)
    return image, chunk_data


def write_image_blosc(filename,data):
    print "write_image_blosc"
    fh = open(filename,'w')
    print "opened", filename
    fh.write(blosc.compress(data,shuffle=blosc.BITSHUFFLE,cname='lz4'))
    print "wrote compressed data"
    fh.close()
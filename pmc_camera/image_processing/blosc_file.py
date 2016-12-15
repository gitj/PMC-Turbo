import numpy as np
import blosc
from pmc_camera.pycamera import dtypes

def load_blosc_file(filename):
    with open(filename, 'rb') as fh:
        data = blosc.decompress(fh.read())
    return data

def load_blosc_image(filename):
    data = load_blosc_file(filename)
    image = np.frombuffer(data[:-dtypes.chunk_num_bytes],dtype='uint16')
    image.shape = dtypes.image_dimensions
    chunk_data = np.frombuffer(data[-dtypes.chunk_num_bytes:],dtype=dtypes.chunk_dtype)
    return image, chunk_data

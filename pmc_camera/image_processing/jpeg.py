import numpy as np
import cStringIO
from PIL import Image

def fast_8bit_image(array):
    return Image.fromarray((array//2**8).astype('uint8'))

def numpy_to_image(array):
    return Image.fromarray(array.astype('int32'),mode='I')

def simple_jpeg(array,scale_by=1,resample=0,**kwargs):
    img = Image.fromarray(array.astype('int32'),mode='I')
    if scale_by != 1:
        x,y = array.shape
        x = int(x*scale_by)
        y = int(y*scale_by)
        size = (x,y)
        img = img.resize(size,resample=resample)
    img = np.asarray(img,dtype='int32')
    max_ = img.max()
    img = img * (255./max_)
    img = Image.fromarray(img.astype('uint8'),mode='L')
    stream = cStringIO.StringIO()
    img.save(stream,format='jpeg',**kwargs)
    stream.seek(0)
    return stream.read()

def image_from_string(data):
    stream  = cStringIO.StringIO(data)
    stream.seek(0)
    return Image.open(stream)
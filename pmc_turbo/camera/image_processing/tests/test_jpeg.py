import numpy as np
from pmc_turbo.camera.image_processing import jpeg

def test_simple_jpeg_all_zeros():
    data = np.zeros((100,123),dtype='uint16')
    result,offset,scale=jpeg.simple_jpeg(data)
    assert offset == 0
    assert scale == 1

def test_simple_jpeg_no_scale():
    data = (np.arange(100,300)[:,None]*np.ones((1,100))).astype('uint16')
    result,offset,scale=jpeg.simple_jpeg(data)
    assert offset == 100
    assert scale == 1

def test_simple_jpeg_scale():
    data = (np.linspace(100,16000,50)[:,None]*np.ones((1,100))).astype('uint16')
    result,offset,scale=jpeg.simple_jpeg(data)
    assert offset == 100
    assert scale == 255./(16000-100)

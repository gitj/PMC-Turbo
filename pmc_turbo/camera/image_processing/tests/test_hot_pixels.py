import glob
import numpy as np
import os
from pmc_turbo.camera.image_processing.hot_pixels import HotPixelMasker
from pmc_turbo.utils.configuration import camera_data_dir

def check_hot_pixel_case(filename):
    pixels = np.load(filename)
    shape = (3232,4864)
    hpm = HotPixelMasker(pixels,shape)
    hpm.process(np.zeros(shape,dtype='uint16'))

def test_hot_pixel_masker():
    hp_files = glob.glob(os.path.join(camera_data_dir,'hot_pixels/*'))
    for filename in hp_files:
        yield check_hot_pixel_case, filename
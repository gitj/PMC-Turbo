import numpy as np
from pmc_turbo.camera.pycamera.pycamera import PyCamera
from pmc_turbo.camera.pycamera.dtypes import image_dimensions

def test_pycamera_methods():
    pc = PyCamera(use_simulated_camera=True)
    pc.set_focus(1000)
    pc.get_focus_max()
    pc.set_exposure_milliseconds(100)
    pc.get_timestamp()
    pc.get_image()
    pc.get_image_with_info()
    pc.get_image_into_buffer(np.zeros(image_dimensions,dtype='uint16'))
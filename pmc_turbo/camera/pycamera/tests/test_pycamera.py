from pmc_turbo.camera.pycamera.pycamera import PyCamera

def test_pycamera_methods():
    pc = PyCamera(use_simulated_camera=True)
    pc.set_focus(1000)
    pc.get_focus_max()
    pc.set_exposure_milliseconds(100)
    pc.get_timestamp()
import numpy as np
import glob
import Queue
import time
import threading

import Pyro4, Pyro4.socketutil

KEYS = [
    'write_timestamp',
    'frame_timestamp_ns',
    'frame_status',
    'frame_id',
    'acquisition_count',
    'lens_status',
    'focus_step',
    'aperture_stop',
    'exposure_us',
    'gain_db',
    'focal_length_mm',
    'filename']


@Pyro4.expose
class FakePipeline:
    # TThe pipeline runs the queue and controls camera settings (like exposure or focus)
    # The queue: Buffers are filled, written to disk, put back into queue to be filled again.
    def __init__(self):

        self.camera_status_dict = {key: None for key in KEYS}
        # This dict informs the status of the camera.
        self.camera_status_dict['write_timestamp'] = True
        self.camera_status_dict['frame_timestamp_ns'] = time.time()
        self.camera_status_dict['acquisition_count'] = 0
        self.camera_status_dict['focus_step'] = 2000
        self.camera_status_dict['aperture_stop'] = 2.0
        self.camera_status_dict['exposure_us'] = 100e6
        self.camera_status_dict['gain_db'] = 0.0
        self.camera_status_dict['focal_length_mm'] = 135

        self.run_pipeline = False
        self.pipeline_thread = None

        self.pipeline_status_dict = {1: True, 2: True, 3: False, 4: False}
        self.filled_buffers = Queue.Queue()
        self.filled_buffers.put(1)
        self.filled_buffers.put(2)
        self.empty_buffers = Queue.Queue()
        self.empty_buffers.put(3)
        self.empty_buffers.put(4)

        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=40000)
        uri = self.daemon.register(self, "fakepipeline")
        print uri

    def run_pyro_loop(self):
        self.daemon.requestLoop()

    def close(self):
        self.daemon.shutdown()

    def fake_pipeline_loop(self):
        while self.run_pipeline == True:
            self.run_fake_pipeline()
            time.sleep(0.5)

    def run_fake_pipeline(self):
        # Just switches buffers from filled to empty and updates status.
        if not self.empty_buffers.empty():
            buffer = self.empty_buffers.get()
            self.filled_buffers.put(buffer)
            self.pipeline_status_dict[buffer] = True

            self.camera_status_dict['acquisition_count'] += 1
            self.camera_status_dict['frame_timestamp_ns'] = time.time()

        if not self.filled_buffers.empty():
            buffer = self.filled_buffers.get()
            self.empty_buffers.put(buffer)
            self.pipeline_status_dict[buffer] = False

    def run_focus_test(self, start, stop, increment):
        # Cycle through different focus steps - return list of files that were the test.
        self.stop_fake_pipeline_thread()
        for focus_step in range(start, stop, increment):
            self.change_camera_param('focus_step', focus_step)
            self.run_fake_pipeline()
            time.sleep(0.5)
        return

    def run_exposure_test(self, start, stop, increment):
        # cycle through different exposures, return list.
        # ImageProcessor gets a list of these images, analyzes them and decides what to do.
        for exposure in range(start, stop, increment):
            self.change_camera_param('exposure_us', exposure)
            self.run_fake_pipeline()
            time.sleep(0.5)
        return

    def start_fake_pipeline_thread(self):
        self.run_pipeline = True
        self.pipeline_thread = threading.Thread(target=self.fake_pipeline_loop)
        self.pipeline_thread.daemon = True
        self.pipeline_thread.start()

    def stop_fake_pipeline_thread(self):
        if self.pipeline_thread and self.pipeline_thread.is_alive():
            self.run_pipeline = False
            self.pipeline_thread.join(timeout=0)

    def get_camera_status(self):
        return self.camera_status_dict

    def get_pipeline_status(self):
        return self.pipeline_status_dict

    def change_camera_param(self, param, value):
        self.camera_status_dict[param] = value
        # self.reconcile_dict_and_params


class FakeImageDealer:
    def __init__(self):
        self.image_path = 'data1/2016-11-18_135mm_focus_test_100_ms_night_window_open/'
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=40001)
        uri = self.daemon.register(self, "fakeimagedealer")
        print uri

    def get_image(self, filename):
        return np.frombuffer(np.load(filename)['image'], dtype='uint16').reshape(3232, 4864)

    def get_recent_images(self, num_images):
        # Grabs num_images most recent images
        path = glob.glob(self.image_path)
        images = [self.get_image(filename) for filename in path[-num_images]]
        return images


class FakeImageProcessor:
    def __init__(self):
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=40002)
        uri = self.daemon.register(self, "fakeimageprocessor")
        print uri

    def do_focus_evaluation(self, images):
        # Ask pipeline to cycling between range of focuses. Analyze results
        return

    def do_autoexposure_evaluation(self, images):
        # This is a bit tricky. Needs to talk to pipeline while it is taking images.
        # Perhaps easier to just do a range -> then ask fake_image_dealer to grab the images.
        return

    def get_postage_stamp(self, image, compression_factor=32):
        return image[::compression_factor, ::compression_factor]

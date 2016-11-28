import numpy as np
import time

class PyCamera():
    def __init__(self,ip="10.0.0.2",num_buffers=0,use_simulated_camera=False):
        if use_simulated_camera:
            from pmc_camera.pycamera._pyvimba._pyvimba_simulator import BasicPyCameraSimulator as _PyCamera
        else:
            from pmc_camera.pycamera._pyvimba._pyvimba import PyCamera as _PyCamera

        self._pc = _PyCamera(ip=ip,num_buffers=num_buffers)
        self._num_buffers = num_buffers
        self.exposure_counts = 0
        self.parameter_names = self._pc.get_parameter_names()

    def get_all_parameters(self):
        return dict([(name,self.get_parameter(name)) for name in self.parameter_names])

    def set_parameter(self,name,value):
        return self._pc.set_parameter_from_string(name,str(value))

    def get_parameter(self,name):
        return self._pc.get_parameter(name)

    def run_feature_command(self,name):
        return self._pc.run_feature_command(name)

    def get_timestamp(self):
        self.run_feature_command("GevTimestampControlLatch")
        return self.get_parameter("GevTimestampValue")

    def compare_timestamps(self):
        now = time.time()
        self.run_feature_command("GevTimestampControlLatch")
        now2 = time.time()
        now = (now+now2)/2.
        ts = float(self.get_parameter("GevTimestampValue"))/1e9
        return now-ts

    def get_image(self):
        return self.get_image_with_info()[1]

    def get_image_with_info(self, dimensions=(3232,4864)):
        """
        get the image data from the next waiting buffer

        There is no guarantee this image is fresh, it could have been sitting in the buffer for an arbitrary amount
        of time.

        Parameters
        ----------
        dimensions : 2-tuple
            Dimensions for the output array when unpacked

        Returns
        -------
            info,data
            info : dict with info from the buffer that contained this image.
                keys include:
                size : 0 if there was a problem getting an image, otherwise number of bytes in the image
                block_id : frame number?
                timestamp : hardware timestamp
            data : uint16 2-D array, reshaped to specified *dimensions*

        """
        info, data = self._pc.get_image()
        if info['size'] > 2**31:
            raise RuntimeError("Image acquisition failed with error code %d" % (info['size']-2**32))
        data = data.view('uint16').reshape(dimensions)
        return info,data

    def get_image_into_buffer(self,npy_array):
        npy_array.shape = (np.product(npy_array.shape),)
        info = self._pc.get_image_into_buffer(npy_array.view('uint8'))
        if info['size'] > 2**31:
            raise RuntimeError("Image acquisition failed with error code %d\n %r" % ((info['size']-2**32),info))
        return info

    def set_exposure_milliseconds(self,milliseconds):
        microseconds = int(np.round(milliseconds*1000.0))
        result = self._pc.set_parameter_from_string("ExposureTimeAbs",str(microseconds))
        if result != 0:
            raise Exception("Camera returned error code %d when trying to set exposure value to %d us." % (result,
                                                                                                          microseconds))

    def get_focus_max(self):
        return int(self._pc.get_parameter("EFLensFocusMax"))

    def set_focus(self,focus_steps):
        result = self._pc.set_parameter_from_string("EFLensFocusCurrent",("%d" % focus_steps))
        if result != 0:
            raise Exception("Camera returned error code %d when trying to set focus value to %d steps." % (result,
                                                                                                          focus_steps))


    def simple_exposure_adjust(self,goal=4000,percentile=99.9,step_factor=1.5,downsample=16,
                               start_fresh=False,verbose=False,max=65535):
        def debug(msg):
            if verbose:
                print msg

        if start_fresh or self.exposure_counts == 0:
            exposure = 1
            last_exposure = 1
        else:
            exposure = self.exposure_counts
            for k in range(self._num_buffers):
                self.get_image()
            debug("flushed buffers")
            d = self.get_image()[1:-1:downsample,1:-1:downsample]
            score = np.percentile(d.flat,percentile)/16.
            if score > goal:
                step_factor = 1/step_factor
            last_exposure = self.exposure_counts


        done = False
        while not done:
            self.set_exposure_counts(exposure)
            debug("Trying %d" % exposure)
            for k in range(self._num_buffers):
                self.get_image()
            debug("flushed buffers")
            d = self.get_image()[1:-1:downsample,1:-1:downsample]
            score = np.percentile(d.flat,percentile)/16.
            debug("current score: %.1f" % score)
            if step_factor > 1 and score > goal:
                debug("goal exceeded, finishing")
                done = True
            elif step_factor < 1 and score < goal:
                debug("goal reached, finishing")
                last_exposure = exposure
                done = True
            else:
                last_exposure = exposure
                exposure = int(np.round(exposure*step_factor))
                if exposure > max:
                    exposure = max
                if exposure == last_exposure:
                    if step_factor > 1:
                        exposure = exposure + 1
                    else:
                        exposure = exposure - 1
                if exposure > max:
                    debug("reached max exposure, finishing")
                    done = True
                if exposure == 1:
                    debug("reached min exposure, finishing")
                    done = True
        self.set_exposure_counts(last_exposure)
        return last_exposure



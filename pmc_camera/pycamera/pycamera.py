import numpy as np

from _pycamera._pycamera import PyCamera as _PyCamera

class PyCamera():
    def __init__(self,ip="10.0.0.2",num_buffers=16):
        self._pc = _PyCamera(ip=ip,num_buffers=num_buffers)
        self._num_buffers = num_buffers
        self.exposure_counts = 0
    def get_image(self):
        return self.get_image_with_info()[1]
    def get_image_with_info(self, dimensions=(3232,4864)):
        """
        get the image data from the next waiting buffer

        There is no guarentee this image is fresh, it could have been sitting in the buffer for an arbitrary amount
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
        data = data.view('uint16').reshape(dimensions)
        return info,data

    def set_exposure_time(self,milliseconds):
        exposure_counts = int(np.round(milliseconds/100.0))
        if exposure_counts > (2**16-1):
            exposure_counts = 2**16-1
        if exposure_counts < 1:
            exposure_counts = 1
        return exposure_counts/100.0

    def set_exposure_counts(self, counts):
        result = self._pc.set_parameter_from_string("FreerunExposureTime", str(counts))
        if result != 0:
            raise Exception("Camera returned error code %d when trying to set exposure value to %d." % (result,counts))
        self.exposure_counts = counts

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



        pass
import numpy as np

from _pycamera._pycamera import PyCamera as _PyCamera

class PyCamera():
    def __init__(self,ip="10.0.0.2",num_buffers=16):
        self._pc = _PyCamera(ip=ip,num_buffers=num_buffers)
        self._num_buffers = num_buffers
        self.exposure_counts = 0
    def get_image(self, unpack=True, dimensions=(3232,4864)):
        """
        get the image data from the next waiting buffer

        There is no guarentee this image is fresh, it could have been sitting in the buffer for an arbitrary amount
        of time.

        Parameters
        ----------
        unpack : bool, defaullt True
            If True, unpack the 12-bit data to 16-bit. Note that the Pleora unpacker puts the 12 bits in the most
            significant bits, so the least significant 4 bits will always be zero. If True, the output will be a 2-D
            array with dimensions given by the *dimensions* argument
        dimensions : 2-tuple
            Dimensions for the output array when unpacked. If None, no reshaping is done, and the output will be 1-D

        Returns
        -------
            data : 1-D or 2-D numpy array
                If unpack is True, dtype will be uint16 and if dimensions is not None, the array will have the
                specified dimensions.
                If unpack is False, dtype will be uint8 (holding the packed 12-bit data) and the array will be 1-D.

        """
        nbytes, data = self._pc.get_image(unpack=unpack)
        if unpack:
            data = data.view('uint16').reshape(dimensions)
        return data

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
                               start_fresh=False,verbose=False):
        def debug(msg):
            if verbose:
                print msg

        if start_fresh or self.exposure_counts == 0:
            exposure = 1
            last_exposure = 1
        else:
            exposure = self.exposure_counts
            for k in range(self._num_buffers):
                self.get_image(unpack=False)
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
                self.get_image(unpack=False)
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
                if exposure == last_exposure:
                    if step_factor > 1:
                        exposure = exposure + 1
                    else:
                        exposure = exposure - 1
                if exposure > 65535:
                    debug("reached max exposure, finishing")
                    done = True
                if exposure == 1:
                    debug("reached min exposure, finishing")
                    done = True
        self.set_exposure_counts(last_exposure)
        return last_exposure



        pass
from _pycamera._pycamera import PyCamera as _PyCamera

class PyCamera():
    def __init__(self,ip="10.0.0.2",num_buffers=16):
        self._pc = _PyCamera(ip=ip,num_buffers=num_buffers)
    def get_image(self, unpack=True, dimensions=(3232,4864)):
        nbytes, data = self._pc.get_image(unpack=unpack)
        if unpack:
            data = data.view('uint16').reshape(dimensions)
        return data

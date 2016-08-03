from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport uint8_t,uint32_t
cimport numpy as np
import numpy as np

cdef extern from "GigECamera.h":
    cdef cppclass GigECamera:
        GigECamera() except +
        void Connect(char *ip)
        vector[string] GetParameterNames()
        int SetParameterFromString(char *name, char *value)
        char *GetParameter(char *name)
        uint32_t GetImage(uint8_t *data)
        uint32_t buffer_size

cdef class PyCamera:
    cdef GigECamera c_camera
    def __cinit__(self, bytes ip):
        self.c_camera.Connect(ip)
    def get_parameter_names(self):
        return self.c_camera.GetParameterNames()
    def set_parameter_from_string(self,bytes name,bytes value):
        return self.c_camera.SetParameterFromString(name,value)
    def get_parameter(self,bytes name):
        return self.c_camera.GetParameter(name)
    def get_image(self):
        cdef np.ndarray[np.uint8_t, ndim=1, mode="c"] data = np.empty((self.c_camera.buffer_size,),dtype='uint8')
        size = self.c_camera.GetImage(&data[0])
        return size,data
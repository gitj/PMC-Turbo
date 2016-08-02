from libcpp.string cimport string
from libcpp.vector cimport vector
cdef extern from "GigECamera.h":
    cdef cppclass GigECamera:
        GigECamera() except +
        void Connect(char *ip)
        vector[string] GetParameterNames()

cdef class PyCamera:
    cdef GigECamera c_camera
    def __cinit__(self, bytes ip):
        self.c_camera.Connect(ip)
    def get_parameter_names(self):
        return self.c_camera.GetParameterNames()
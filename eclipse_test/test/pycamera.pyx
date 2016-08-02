from libcpp.string cimport string
from libcpp.vector cimport vector
cdef extern from "GigECamera.h":
    cdef cppclass GigECamera:
        GigECamera() except +
        void Connect(char *ip)
        vector[string] GetParameterNames()
        int SetParameterFromString(char *name, char *value)
        char *GetParameter(char *name)

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
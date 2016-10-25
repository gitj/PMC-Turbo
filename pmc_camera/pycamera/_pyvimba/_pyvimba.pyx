from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport uint8_t,uint32_t,uint64_t
from libcpp cimport bool as cbool
from libc.stdlib cimport malloc
import numpy as np
cimport numpy as np
np.import_array()

cdef extern from "numpy/arrayobject.h":
    void PyArray_ENABLEFLAGS(np.ndarray arr, int flags)

cdef extern from "GigECamera.h":
    cdef cppclass GigECamera:
        GigECamera() except +
        void Connect(char *ip, uint32_t num_buffers)
        vector[string] GetParameterNames()
        int SetParameterFromString(char *name, char *value)
        int RunFeatureCommand(char *name)
        string GetParameter(char *name)
        uint32_t GetImageSimple(uint8_t *data)
        uint32_t GetImage(uint8_t *data, uint64_t &frame_id, uint64_t &timestamp, uint32_t &frame_status)
        uint32_t buffer_size
        uint32_t QueueFrameFromBuffer(uint8_t *data, frame_info *p_info)
        uint32_t StartCapture()
        uint32_t EndCapture()
#        void GetBuffer(PvBuffer *output)
    cdef packed struct frame_info:
        uint64_t frame_id
        uint64_t timestamp
        uint32_t frame_status
        uint32_t is_filled

cdef class PyCamera:
    cdef GigECamera c_camera
    def __cinit__(self, bytes ip, int num_buffers):
        self.c_camera.Connect(ip, num_buffers)
    def get_parameter_names(self):
        return self.c_camera.GetParameterNames()
    def start_capture(self):
        return self.c_camera.StartCapture()
    def end_capture(self):
        return self.c_camera.EndCapture()
    def set_parameter_from_string(self,bytes name,bytes value):
        return self.c_camera.SetParameterFromString(name,value)
    def get_parameter(self,bytes name):
        return self.c_camera.GetParameter(name)
    def run_feature_command(self,bytes name):
        return self.c_camera.RunFeatureCommand(name)
    def get_image(self):
        cdef uint32_t nybtes 
        nbytes =  self.c_camera.buffer_size

        cdef uint8_t *buffer = <uint8_t *>malloc(nbytes)
        cdef uint64_t frame_id, buffer_id, reception_time, timestamp
        cdef uint32_t frame_status
        size = self.c_camera.GetImage(buffer, frame_id, timestamp, frame_status)
#        size = self.c_camera.GetImageSimple(buffer)
        cdef np.npy_intp *dims = [nbytes,]
        cdef np.ndarray[np.uint8_t, ndim=1, mode="c"] data = np.PyArray_SimpleNewFromData(1,dims,np.NPY_UINT8,buffer)
        PyArray_ENABLEFLAGS(data, np.NPY_OWNDATA)
        info = dict(size=size, frame_id=frame_id, timestamp=timestamp,frame_status=frame_status)
        return info, data

    def get_image_into_buffer(self, np.ndarray[np.uint8_t] data):
        cdef uint8_t *buffer = <uint8_t *> data.data
        cdef uint64_t frame_id, timestamp
        cdef uint32_t frame_status
        size = self.c_camera.GetImage(buffer, frame_id, timestamp, frame_status)
        info = dict(size=size,frame_id=frame_id,
                    timestamp=timestamp, frame_status=frame_status)
        return info
    def queue_buffer(self, np.ndarray[np.uint8_t] data, np.ndarray[frame_info] info):
        cdef uint8_t *buffer = <uint8_t *> data.data
        result = self.c_camera.QueueFrameFromBuffer(buffer, <frame_info *>info.data)
        return result

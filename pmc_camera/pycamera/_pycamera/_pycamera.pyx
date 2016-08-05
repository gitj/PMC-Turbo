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

cdef extern from "PvBuffer.h":
    cdef enum PvPayloadType:
        PvPayloadTypeImage = 1
    cdef cppclass PvBuffer:
        PvBuffer( PvPayloadType aPayloadType = PvPayloadTypeImage )
        PvPayloadType GetPayloadType()
        uint8_t * GetDataPointer()
        uint64_t GetID()
        void SetID( uint64_t aValue )

        cbool IsExtendedID()
        cbool IsAttached()
        cbool IsAllocated()
    
        uint32_t GetAcquiredSize()
        uint32_t GetRequiredSize()
        uint32_t GetSize()
        uint64_t GetBlockID() 
#        PvResult GetOperationResult() 
        uint64_t GetTimestamp() 
        uint64_t GetReceptionTime() 
    
#        PvResult SetTimestamp( uint64_t aTimestamp )
#        PvResult SetBlockID( uint64_t aBlockID )
#        PvResult SetReceptionTime( uint64_t aReceptionTime )
    
        uint32_t GetPacketsRecoveredCount() 
        uint32_t GetPacketsRecoveredSingleResendCount() 
        uint32_t GetResendGroupRequestedCount() 
        uint32_t GetResendPacketRequestedCount() 
        uint32_t GetLostPacketCount() 
        uint32_t GetIgnoredPacketCount() 
        uint32_t GetRedundantPacketCount() 
        uint32_t GetPacketOutOfOrderCount() 
    
#        PvResult GetMissingPacketIdsCount( uint32_t& aCount );
#        PvResult GetMissingPacketIds( uint32_t aIndex, uint32_t& aPacketIdLow, uint32_t& aPacketIdHigh );
    
        cbool HasChunks() 
        uint32_t GetChunkCount();
#        PvResult GetChunkIDByIndex( uint32_t aIndex, uint32_t &aID );
#        uint32_t GetChunkSizeByIndex( uint32_t aIndex );
#        uint32_t GetChunkSizeByID( uint32_t aID );
        const uint8_t *GetChunkRawDataByIndex( uint32_t aIndex );
        const uint8_t *GetChunkRawDataByID( uint32_t aID );
        uint32_t GetPayloadSize() 
    
        cbool IsHeaderValid() 
        cbool IsTrailerValid()
        
cdef class PyPvBuffer:
    cdef PvBuffer c_pvbuffer
    def get_size(self):
        return self.c_pvbuffer.GetSize()
    def get_data(self):
        cdef uint8_t[:] bufview = <uint8_t[:self.c_pvbuffer.GetSize()]> self.c_pvbuffer.GetDataPointer()
        return np.asarray(bufview)
    def get_block_id(self):
        return self.c_pvbuffer.GetBlockID()
    def get_timestamp(self):
        return self.c_pvbuffer.GetTimestamp()
    def get_reception_time(self):
        return self.c_pvbuffer.GetReceptionTime()


cdef extern from "GigECamera.h":
    cdef cppclass GigECamera:
        GigECamera() except +
        void Connect(char *ip, uint32_t num_buffers)
        vector[string] GetParameterNames()
        int SetParameterFromString(char *name, char *value)
        char *GetParameter(char *name)
        uint32_t GetImage(uint8_t *data, cbool unpack)
        uint32_t buffer_size
        void GetBuffer(PvBuffer *output)

cdef class PyCamera:
    cdef GigECamera c_camera
    def __cinit__(self, bytes ip, int num_buffers):
        self.c_camera.Connect(ip, num_buffers)
    def get_parameter_names(self):
        return self.c_camera.GetParameterNames()
    def set_parameter_from_string(self,bytes name,bytes value):
        return self.c_camera.SetParameterFromString(name,value)
    def get_parameter(self,bytes name):
        return self.c_camera.GetParameter(name)
    def get_image(self,unpack=True):
        cdef uint32_t nybtes 
        nbytes =  self.c_camera.buffer_size
        if unpack:
            nbytes = nbytes*16//12
        cdef uint8_t *buffer = <uint8_t *>malloc(nbytes)
        size = self.c_camera.GetImage(buffer, unpack)
        cdef np.npy_intp *dims = [nbytes,]
        cdef np.ndarray[np.uint8_t, ndim=1, mode="c"] data = np.PyArray_SimpleNewFromData(1,dims,np.NPY_UINT8,buffer)
        PyArray_ENABLEFLAGS(data, np.NPY_OWNDATA)
        return size,data
    def get_buffer(self):
        output = PyPvBuffer()
        self.c_camera.GetBuffer(&output.c_pvbuffer)
        return output
    
"""

    PvPayloadType GetPayloadType() 
    
    PvImage *GetImage();
    const PvImage *GetImage() 
    PvRawData *GetRawData();
    const PvRawData *GetRawData() 

    const uint8_t * GetDataPointer() 
    uint8_t * GetDataPointer();

    uint64_t GetID() 
    void SetID( uint64_t aValue );

    cbool IsExtendedID() 
    cbool IsAttached() 
    cbool IsAllocated() 

    uint32_t GetAcquiredSize() 
    uint32_t GetRequiredSize() 
    uint32_t GetSize() 

    PvResult Reset( PvPayloadType aPayloadType = PvPayloadTypeImage );

    PvResult Alloc( uint32_t aSize );
    void Free();

    PvResult Attach( void * aBuffer, uint32_t aSize );
    uint8_t *Detach();

    uint64_t GetBlockID() 
    PvResult GetOperationResult() 
    uint64_t GetTimestamp() 
    uint64_t GetReceptionTime() 

    PvResult SetTimestamp( uint64_t aTimestamp );
    PvResult SetBlockID( uint64_t aBlockID );
    PvResult SetReceptionTime( uint64_t aReceptionTime );

    uint32_t GetPacketsRecoveredCount() 
    uint32_t GetPacketsRecoveredSingleResendCount() 
    uint32_t GetResendGroupRequestedCount() 
    uint32_t GetResendPacketRequestedCount() 
    uint32_t GetLostPacketCount() 
    uint32_t GetIgnoredPacketCount() 
    uint32_t GetRedundantPacketCount() 
    uint32_t GetPacketOutOfOrderCount() 

    PvResult GetMissingPacketIdsCount( uint32_t& aCount );
    PvResult GetMissingPacketIds( uint32_t aIndex, uint32_t& aPacketIdLow, uint32_t& aPacketIdHigh );

    cbool HasChunks() 
    uint32_t GetChunkCount();
    PvResult GetChunkIDByIndex( uint32_t aIndex, uint32_t &aID );
    uint32_t GetChunkSizeByIndex( uint32_t aIndex );
    uint32_t GetChunkSizeByID( uint32_t aID );
    const uint8_t *GetChunkRawDataByIndex( uint32_t aIndex );
    const uint8_t *GetChunkRawDataByID( uint32_t aID );
    uint32_t GetPayloadSize() 

    cbool IsHeaderValid() 
    cbool IsTrailerValid() """
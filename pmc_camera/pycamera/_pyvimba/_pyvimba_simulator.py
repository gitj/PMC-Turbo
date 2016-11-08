import numpy as np
import time
from pmc_camera.pycamera.dtypes import frame_info_dtype
gt4907_parameter_names = ["AcquisitionAbort", "AcquisitionFrameCount", "AcquisitionFrameRateAbs", "AcquisitionFrameRateLimit", "AcquisitionMode", "AcquisitionStart", "AcquisitionStop", "ActionDeviceKey", "ActionGroupKey", "ActionGroupMask", "ActionSelector", "BandwidthControlMode", "BinningHorizontal", "BinningVertical", "ChunkModeActive", "DSPSubregionBottom", "DSPSubregionLeft", "DSPSubregionRight", "DSPSubregionTop", "DecimationHorizontal", "DecimationVertical", "DefectMaskEnable", "DeviceFirmwareVersion", "DeviceID", "DeviceModelName", "DevicePartNumber", "DeviceScanType", "DeviceTemperature", "DeviceTemperatureSelector", "DeviceUserID", "DeviceVendorName", "EFLensFStopCurrent", "EFLensFStopDecrease", "EFLensFStopIncrease", "EFLensFStopMax", "EFLensFStopMin", "EFLensFStopStepSize", "EFLensFocusCurrent", "EFLensFocusDecrease", "EFLensFocusIncrease", "EFLensFocusMax", "EFLensFocusMin", "EFLensFocusStepSize", "EFLensFocusSwitch", "EFLensID", "EFLensInitialize", "EFLensLastError", "EFLensState", "EFLensZoomCurrent", "EFLensZoomMax", "EFLensZoomMin", "EventAcquisitionEnd", "EventAcquisitionEndFrameID", "EventAcquisitionEndTimestamp", "EventAcquisitionRecordTrigger", "EventAcquisitionRecordTriggerFrameID", "EventAcquisitionRecordTriggerTimestamp", "EventAcquisitionStart", "EventAcquisitionStartFrameID", "EventAcquisitionStartTimestamp", "EventAction0", "EventAction0FrameID", "EventAction0Timestamp", "EventAction1", "EventAction1FrameID", "EventAction1Timestamp", "EventError", "EventErrorFrameID", "EventErrorTimestamp", "EventExposureEnd", "EventExposureEndFrameID", "EventExposureEndTimestamp", "EventExposureStart", "EventExposureStartFrameID", "EventExposureStartTimestamp", "EventFrameTrigger", "EventFrameTriggerFrameID", "EventFrameTriggerReady", "EventFrameTriggerReadyFrameID", "EventFrameTriggerReadyTimestamp", "EventFrameTriggerTimestamp", "EventLine1FallingEdge", "EventLine1FallingEdgeFrameID", "EventLine1FallingEdgeTimestamp", "EventLine1RisingEdge", "EventLine1RisingEdgeFrameID", "EventLine1RisingEdgeTimestamp", "EventLine2FallingEdge", "EventLine2FallingEdgeFrameID", "EventLine2FallingEdgeTimestamp", "EventLine2RisingEdge", "EventLine2RisingEdgeFrameID", "EventLine2RisingEdgeTimestamp", "EventNotification", "EventOverflow", "EventOverflowFrameID", "EventOverflowTimestamp", "EventPtpSyncLocked", "EventPtpSyncLockedFrameID", "EventPtpSyncLockedTimestamp", "EventPtpSyncLost", "EventPtpSyncLostFrameID", "EventPtpSyncLostTimestamp", "EventSelector", "EventsEnable1", "ExposureAuto", "ExposureAutoAdjustTol", "ExposureAutoAlg", "ExposureAutoMax", "ExposureAutoMin", "ExposureAutoOutliers", "ExposureAutoRate", "ExposureAutoTarget", "ExposureMode", "ExposureTimeAbs", "FirmwareVerBuild", "FirmwareVerMajor", "FirmwareVerMinor", "GVCPCmdRetries", "GVCPCmdTimeout", "GVSPAdjustPacketSize", "GVSPBurstSize", "GVSPDriver", "GVSPFilterVersion", "GVSPHostReceiveBuffers", "GVSPMaxLookBack", "GVSPMaxRequests", "GVSPMaxWaitSize", "GVSPMissingSize", "GVSPPacketSize", "GVSPTiltingSize", "GVSPTimeout", "Gain", "GainAuto", "GainAutoAdjustTol", "GainAutoMax", "GainAutoMin", "GainAutoOutliers", "GainAutoRate", "GainAutoTarget", "GainSelector", "Gamma", "GevCurrentDefaultGateway", "GevCurrentIPAddress", "GevCurrentSubnetMask", "GevDeviceMACAddress", "GevHeartbeatInterval", "GevHeartbeatTimeout", "GevIPConfigurationMode", "GevPersistentDefaultGateway", "GevPersistentIPAddress", "GevPersistentSubnetMask", "GevSCPSPacketSize", "GevTimestampControlLatch", "GevTimestampControlReset", "GevTimestampTickFrequency", "GevTimestampValue", "Height", "HeightMax", "ImageSize", "LUTAddress", "LUTBitDepthIn", "LUTBitDepthOut", "LUTEnable", "LUTIndex", "LUTLoadAll", "LUTMode", "LUTSaveAll", "LUTSelector", "LUTSizeBytes", "LUTValue", "MulticastEnable", "MulticastIPAddress", "NonImagePayloadSize", "OffsetX", "OffsetY", "PayloadSize", "PixelFormat", "PtpAcquisitionGateTime", "PtpMode", "PtpStatus", "RecorderPreEventCount", "ReverseX", "ReverseY", "SensorBits", "SensorDigitizationTaps", "SensorHeight", "SensorTaps", "SensorType", "SensorWidth", "StatFrameDelivered", "StatFrameDropped", "StatFrameRate", "StatFrameRescued", "StatFrameShoved", "StatFrameUnderrun", "StatLocalRate", "StatPacketErrors", "StatPacketMissed", "StatPacketReceived", "StatPacketRequested", "StatPacketResent", "StatTimeElapsed", "StreamAnnounceBufferMinimum", "StreamAnnouncedBufferCount", "StreamBufferHandlingMode", "StreamBytesPerSecond", "StreamFrameRateConstrain", "StreamHoldCapacity", "StreamHoldEnable", "StreamID", "StreamType", "StrobeDelay", "StrobeDuration", "StrobeDurationMode", "StrobeSource", "SyncInGlitchFilter", "SyncInLevels", "SyncInSelector", "SyncOutLevels", "SyncOutPolarity", "SyncOutSelector", "SyncOutSource", "TriggerActivation", "TriggerDelayAbs", "TriggerMode", "TriggerOverlap", "TriggerSelector", "TriggerSoftware", "TriggerSource", "UserSetDefaultSelector", "UserSetLoad", "UserSetSave", "UserSetSelector", "VsubValue", "Width", "WidthMax"]

class BasicPyCameraSimulator:
    def __init__(self,ip=None,num_buffers=None):
        self.bytes_per_image = 3232*4864*2
    def get_parameter_names(self):
        return gt4907_parameter_names[:]
    def start_capture(self):
        return 0
    def end_capture(self):
        return 0
    def set_parameter_from_string(self,name,value):
        if name in gt4907_parameter_names:
            return 0
        else:
            return -3
    def get_parameter(self,name):
        if name in gt4907_parameter_names:
            return "0"
        else:
            return 'Error No Such Feature'
    def run_feature_command(self,name):
        if name in gt4907_parameter_names:
            return 0
        else:
            return -3
    def get_image(self):
        data = np.empty((self.bytes_per_image,),dtype=np.uint8)

        info = dict(size=self.bytes_per_image, frame_id=0, timestamp=int(time.time()*1e9),frame_status=0)
        return info, data

    def get_image_into_buffer(self,data):
        info = dict(size=self.bytes_per_image, frame_id=0, timestamp=int(time.time()*1e9),frame_status=0)
        return info
    def queue_buffer(self, data, info):
        info = info.view(frame_info_dtype)
        info[0]['is_filled'] = 1
        info[0]['frame_id'] = 0
        info[0]['frame_status'] = 0
        info[0]['timestamp'] = int(time.time()*1e9)
        result = 0
        return result

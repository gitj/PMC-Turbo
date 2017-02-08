import Queue
import logging
import threading
import time

import numpy as np

from pmc_turbo.camera.pycamera.dtypes import frame_info_dtype,chunk_num_bytes

gt4907_parameter_names = ["AcquisitionAbort", "AcquisitionFrameCount", "AcquisitionFrameRateAbs", "AcquisitionFrameRateLimit", "AcquisitionMode", "AcquisitionStart", "AcquisitionStop", "ActionDeviceKey", "ActionGroupKey", "ActionGroupMask", "ActionSelector", "BandwidthControlMode", "BinningHorizontal", "BinningVertical", "ChunkModeActive", "DSPSubregionBottom", "DSPSubregionLeft", "DSPSubregionRight", "DSPSubregionTop", "DecimationHorizontal", "DecimationVertical", "DefectMaskEnable", "DeviceFirmwareVersion", "DeviceID", "DeviceModelName", "DevicePartNumber", "DeviceScanType", "DeviceTemperature", "DeviceTemperatureSelector", "DeviceUserID", "DeviceVendorName", "EFLensFStopCurrent", "EFLensFStopDecrease", "EFLensFStopIncrease", "EFLensFStopMax", "EFLensFStopMin", "EFLensFStopStepSize", "EFLensFocusCurrent", "EFLensFocusDecrease", "EFLensFocusIncrease", "EFLensFocusMax", "EFLensFocusMin", "EFLensFocusStepSize", "EFLensFocusSwitch", "EFLensID", "EFLensInitialize", "EFLensLastError", "EFLensState", "EFLensZoomCurrent", "EFLensZoomMax", "EFLensZoomMin", "EventAcquisitionEnd", "EventAcquisitionEndFrameID", "EventAcquisitionEndTimestamp", "EventAcquisitionRecordTrigger", "EventAcquisitionRecordTriggerFrameID", "EventAcquisitionRecordTriggerTimestamp", "EventAcquisitionStart", "EventAcquisitionStartFrameID", "EventAcquisitionStartTimestamp", "EventAction0", "EventAction0FrameID", "EventAction0Timestamp", "EventAction1", "EventAction1FrameID", "EventAction1Timestamp", "EventError", "EventErrorFrameID", "EventErrorTimestamp", "EventExposureEnd", "EventExposureEndFrameID", "EventExposureEndTimestamp", "EventExposureStart", "EventExposureStartFrameID", "EventExposureStartTimestamp", "EventFrameTrigger", "EventFrameTriggerFrameID", "EventFrameTriggerReady", "EventFrameTriggerReadyFrameID", "EventFrameTriggerReadyTimestamp", "EventFrameTriggerTimestamp", "EventLine1FallingEdge", "EventLine1FallingEdgeFrameID", "EventLine1FallingEdgeTimestamp", "EventLine1RisingEdge", "EventLine1RisingEdgeFrameID", "EventLine1RisingEdgeTimestamp", "EventLine2FallingEdge", "EventLine2FallingEdgeFrameID", "EventLine2FallingEdgeTimestamp", "EventLine2RisingEdge", "EventLine2RisingEdgeFrameID", "EventLine2RisingEdgeTimestamp", "EventNotification", "EventOverflow", "EventOverflowFrameID", "EventOverflowTimestamp", "EventPtpSyncLocked", "EventPtpSyncLockedFrameID", "EventPtpSyncLockedTimestamp", "EventPtpSyncLost", "EventPtpSyncLostFrameID", "EventPtpSyncLostTimestamp", "EventSelector", "EventsEnable1", "ExposureAuto", "ExposureAutoAdjustTol", "ExposureAutoAlg", "ExposureAutoMax", "ExposureAutoMin", "ExposureAutoOutliers", "ExposureAutoRate", "ExposureAutoTarget", "ExposureMode", "ExposureTimeAbs", "FirmwareVerBuild", "FirmwareVerMajor", "FirmwareVerMinor", "GVCPCmdRetries", "GVCPCmdTimeout", "GVSPAdjustPacketSize", "GVSPBurstSize", "GVSPDriver", "GVSPFilterVersion", "GVSPHostReceiveBuffers", "GVSPMaxLookBack", "GVSPMaxRequests", "GVSPMaxWaitSize", "GVSPMissingSize", "GVSPPacketSize", "GVSPTiltingSize", "GVSPTimeout", "Gain", "GainAuto", "GainAutoAdjustTol", "GainAutoMax", "GainAutoMin", "GainAutoOutliers", "GainAutoRate", "GainAutoTarget", "GainSelector", "Gamma", "GevCurrentDefaultGateway", "GevCurrentIPAddress", "GevCurrentSubnetMask", "GevDeviceMACAddress", "GevHeartbeatInterval", "GevHeartbeatTimeout", "GevIPConfigurationMode", "GevPersistentDefaultGateway", "GevPersistentIPAddress", "GevPersistentSubnetMask", "GevSCPSPacketSize", "GevTimestampControlLatch", "GevTimestampControlReset", "GevTimestampTickFrequency", "GevTimestampValue", "Height", "HeightMax", "ImageSize", "LUTAddress", "LUTBitDepthIn", "LUTBitDepthOut", "LUTEnable", "LUTIndex", "LUTLoadAll", "LUTMode", "LUTSaveAll", "LUTSelector", "LUTSizeBytes", "LUTValue", "MulticastEnable", "MulticastIPAddress", "NonImagePayloadSize", "OffsetX", "OffsetY", "PayloadSize", "PixelFormat", "PtpAcquisitionGateTime", "PtpMode", "PtpStatus", "RecorderPreEventCount", "ReverseX", "ReverseY", "SensorBits", "SensorDigitizationTaps", "SensorHeight", "SensorTaps", "SensorType", "SensorWidth", "StatFrameDelivered", "StatFrameDropped", "StatFrameRate", "StatFrameRescued", "StatFrameShoved", "StatFrameUnderrun", "StatLocalRate", "StatPacketErrors", "StatPacketMissed", "StatPacketReceived", "StatPacketRequested", "StatPacketResent", "StatTimeElapsed", "StreamAnnounceBufferMinimum", "StreamAnnouncedBufferCount", "StreamBufferHandlingMode", "StreamBytesPerSecond", "StreamFrameRateConstrain", "StreamHoldCapacity", "StreamHoldEnable", "StreamID", "StreamType", "StrobeDelay", "StrobeDuration", "StrobeDurationMode", "StrobeSource", "SyncInGlitchFilter", "SyncInLevels", "SyncInSelector", "SyncOutLevels", "SyncOutPolarity", "SyncOutSelector", "SyncOutSource", "TriggerActivation", "TriggerDelayAbs", "TriggerMode", "TriggerOverlap", "TriggerSelector", "TriggerSoftware", "TriggerSource", "UserSetDefaultSelector", "UserSetLoad", "UserSetSave", "UserSetSelector", "VsubValue", "Width", "WidthMax"]

logger = logging.getLogger(__name__)

class BasicPyCameraSimulator:
    def __init__(self,ip=None,num_buffers=None):
        self.bytes_per_image = 3232*4864*2 + chunk_num_bytes
        self._time_per_image = 0.4
        self._buffer_queue = Queue.Queue()
        self._quit = False
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

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
    def queue_buffer(self, data, raw_info):
        logger.debug("queuing buffer")
        info = raw_info.view(frame_info_dtype)
        info[0]['is_filled'] = 0
        info[0]['frame_id'] = 0
        info[0]['frame_status'] = 0
        info[0]['timestamp'] = int(time.time()*1e9)
        self._buffer_queue.put((data,raw_info))
        result = 0
        return result

    def quit(self):
        self._quit = True
        try:
            self._thread.join(3)
        except Exception:
            logger.exception("Failed to quit thread")
            pass
    def _run(self):
        while not self._quit:
            try:
                data,info = self._buffer_queue.get(block=False)
                logger.debug("got buffer, marking it filled")
                info = info.view(frame_info_dtype)
                info[0]['is_filled'] = 1
                info[0]['frame_id'] = 0
                info[0]['frame_status'] = 0
                info[0]['timestamp'] = int(time.time()*1e9)

            except Queue.Empty:
                pass
            time.sleep(self._time_per_image)
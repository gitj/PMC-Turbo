import logging
import multiprocessing as mp
import os
import tempfile
import time
from Queue import Empty as EmptyException

from pmc_turbo.camera.utils.error_counter import CounterCollection

logger = logging.getLogger(__name__)
import Pyro4
import numpy as np

Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.SERIALIZERS_ACCEPTED = {'pickle','json'}
Pyro4.config.SERIALIZER = 'pickle'


from pmc_turbo.camera.pycamera.dtypes import frame_info_dtype

camera_status_columns = ["total_frames", "camera_timestamp_offset", "main_temperature", "sensor_temperature",
                         "AcquisitionFrameCount", "AcquisitionFrameRateAbs", "AcquisitionFrameRateLimit",
                         "AcquisitionMode", "ChunkModeActive",
                         "DeviceTemperature", "DeviceTemperatureSelector", "EFLensFStopCurrent",
                         "EFLensFStopMax", "EFLensFStopMin", "EFLensFStopStepSize",
                         "EFLensFocusCurrent", "EFLensFocusMax", "EFLensFocusMin", "EFLensFocusSwitch", "EFLensID",
                         "EFLensLastError", "EFLensState",
                         "ExposureAuto", "ExposureAutoAdjustTol", "ExposureAutoAlg", "ExposureAutoMax",
                         "ExposureAutoMin",
                         "ExposureAutoOutliers", "ExposureAutoRate", "ExposureAutoTarget", "ExposureMode",
                         "ExposureTimeAbs",
                         "Gain", "GainAuto", "GevTimestampValue", "PixelFormat", "PtpAcquisitionGateTime",
                         "PtpMode", "PtpStatus",
                         "StatFrameDelivered", "StatFrameDropped", "StatFrameRate", "StatFrameRescued",
                         "StatFrameShoved", "StatFrameUnderrun", "StatLocalRate", "StatPacketErrors",
                         "StatPacketMissed",
                         "StatPacketReceived", "StatPacketRequested", "StatPacketResent", "StatTimeElapsed",
                         "StreamAnnouncedBufferCount", "StreamBytesPerSecond",
                         "StreamHoldEnable", "StreamID", "StreamType", "TriggerMode", "TriggerSource"]


LOG_DIR='/home/pmc/logs/housekeeping/camera'
COUNTER_DIR = '/home/pmc/logs/counters'

class AcquireImagesProcess:
    def __init__(self, raw_image_buffers, acquire_image_output_queue, acquire_image_input_queue,
                 command_queue, command_result_queue, info_buffer,status,use_simulated_camera,uri,log_dir = LOG_DIR,counter_dir=COUNTER_DIR):
        self.data_buffers = raw_image_buffers
        self.input_queue = acquire_image_input_queue
        self.output_queue = acquire_image_output_queue
        self.command_queue = command_queue
        self.command_result_queue = command_result_queue
        self.info_buffer = info_buffer
        self.use_simulated_camera = use_simulated_camera
        self.uri = uri
        self.counter_dir = counter_dir
        if self.use_simulated_camera:
            self.log_dir = tempfile.mkdtemp("simulated_camera_logs")
        else:
            self.log_dir = log_dir
        self.status = status
        self.status.value="starting"
        self.status_log_filename = None
        self.status_log_file = None
        self.status_log_last_update = 0
        self.status_log_update_interval = 10
        self.columns = camera_status_columns
        self.child = mp.Process(target=self.run)
        #self.child.start()

    def create_log_file(self,columns):
        try:
            os.makedirs(self.log_dir)
        except OSError:
            pass

        self.status_log_filename = os.path.join(self.log_dir, (time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.status_log_file = open(self.status_log_filename, 'a')
        self.status_log_file.write('# %s %s %s %s\n' %
                                   (self.pc.get_parameter("DeviceModelName"),
                                    self.pc.get_parameter("DeviceID"),
                                    self.pc.get_parameter("DeviceFirmwareVersion"),
                                    self.pc.get_parameter("GevDeviceMACAddress")))
        self.status_log_file.write(','.join(['epoch'] + columns) + '\n')


    def get_temperatures(self):
        self.pc.set_parameter("DeviceTemperatureSelector","Main")
        main = self.pc.get_parameter("DeviceTemperature")
        self.pc.set_parameter("DeviceTemperatureSelector","Sensor")
        sensor = self.pc.get_parameter("DeviceTemperature")
        return dict(main_temperature=main,sensor_temperature=sensor)

    def log_status(self,status_update):
        if time.time() - self.status_log_last_update < self.status_log_update_interval:
            return
        self.status_log_last_update = time.time()
        status_update = status_update.copy()
        camera_status = status_update.pop('all_camera_parameters')
        status_update.update(camera_status)
        if self.status_log_file is None:
            self.create_log_file(self.columns)
        values = [status_update['camera_status_update_at']]
        for column in self.columns:
            values.append(status_update[column])
        self.status_log_file.write(','.join(['%s' % value for value in values]) + '\n')
        self.status_log_file.flush()



    def run(self):
        self.pipeline = Pyro4.Proxy(uri=self.uri)
        self.pipeline._pyroTimeout = 0
        self.counters = CounterCollection('acquire_images',self.counter_dir)
        self.counters.camera_armed.reset()
        self.counters.buffer_queued.reset()
        self.counters.error_queuing_buffer.reset()
        self.counters.command_sent.reset()
        self.counters.parameter_set.reset()
        self.counters.command_non_zero_result.reset()
        self.counters.waiting_for_buffer.reset()
        self.counters.buffer_filled.reset()
        self.counters.getting_parameters.reset()
        self.counters.waiting.reset()
        self.counters.waiting.lazy = True # waiting gets incremented hundreds of times per second, no need to record every increment

        # Setup
        frame_number = 0
        from pmc_turbo import camera
        self.status.value = "initializing camera"
        self.pc = camera.PyCamera("10.0.0.2", use_simulated_camera=self.use_simulated_camera)
        self.pc.set_parameter("PtpMode","Slave")
        self.pc.set_parameter("ChunkModeActive","1")
        self.pc.set_parameter("AcquisitionFrameCount","2")
        self.pc.set_parameter('AcquisitionMode',"MultiFrame")
        self.pc.set_parameter("StreamFrameRateConstrain","0")
        self.pc.set_parameter('AcquisitionFrameRateAbs',"6.25")
        self.pc.set_parameter('TriggerSource','FixedRate')
        self.pc.set_parameter('ExposureTimeAbs',"100000")
        self.pc.set_parameter('EFLensFocusCurrent',"4800")
        self.payload_size = int(self.pc.get_parameter('PayloadSize'))
        logger.debug("payload size: %d" % self.payload_size)


        self.pc._pc.start_capture()

        camera_parameters_last_updated = 0

        last_trigger = int(time.time()+1)
        buffers_on_camera = set()
        self.acquisition_start_time = time.time()
        # Run loop
        exit_request = False
        self.status.value = "idle"

        while True:
            while True:
                try:
                    ready_to_queue = self.input_queue.get_nowait()
                except EmptyException:
                    break
                if ready_to_queue is None:
                    exit_request = True
                    break
                self.status.value = "queueing buffer %d" % ready_to_queue
                image_buffer = np.frombuffer(self.data_buffers[ready_to_queue].get_obj(), dtype='uint8')
                #cast the buffer array using the compound data type that has a spot for each info field
                npy_info_buffer = np.frombuffer(self.info_buffer[ready_to_queue].get_obj(),dtype=frame_info_dtype)
                result = self.pc._pc.queue_buffer(image_buffer,npy_info_buffer)
                if result != 0:
                    logger.error("Errorcode while queueing buffer: %r" % result)
                    self.counters.error_queuing_buffer.increment()
                else:
                    buffers_on_camera.add(ready_to_queue)
                    self.counters.buffer_queued.increment()
            if exit_request:
                break
            if time.time() > last_trigger + 0.5:
                gate_time = int(time.time()+1)
                if not self.command_queue.empty():
                    name,value,tag = self.command_queue.get()
                    self.status.value = "sending command"
                    if value is None:
                        result = self.pc.run_feature_command(name)
                        self.counters.command_sent.increment()
                    else:
                        result = self.pc.set_parameter(name,value)
                        self.counters.parameter_set.increment()
                    if result:
                        logger.error("Errorcode %r while executing command %s:%r" % (result,name,value))
                        self.counters.command_non_zero_result.increment()
                    gate_time = int(time.time()+1)  # update gate time in case some time has elapsed while executing
                    # command
                    self.command_result_queue.put((tag,name,value,result,gate_time))
                self.status.value = "arming camera"
                self.pc.set_parameter('PtpAcquisitionGateTime',str(int(gate_time*1e9)))
                time.sleep(0.1)
                self.pc.run_feature_command("AcquisitionStart")
                last_trigger = gate_time
                self.counters.camera_armed.increment()

            if not buffers_on_camera:
                self.status.value = "waiting for buffer on camera"
                time.sleep(0.001)
                self.counters.waiting_for_buffer.increment()
            else:
                self.status.value = "checking buffers"
            num_buffers_filled = 0
            for buffer_id in list(buffers_on_camera):
                npy_info_buffer = np.frombuffer(self.info_buffer[buffer_id].get_obj(),dtype=frame_info_dtype)
                if npy_info_buffer[0]['is_filled']:
                    self.status.value = 'buffer %d was filled by camera' % buffer_id
                    logger.debug(self.status.value)
                    self.output_queue.put(buffer_id)
                    buffers_on_camera.remove(buffer_id)
                    frame_number += 1
                    num_buffers_filled +=1
                    self.counters.buffer_filled.increment()
            if num_buffers_filled == 0:
                self.status.value = "waiting for buffer to be filled"
                update_at = time.time()
                if update_at - camera_parameters_last_updated > 1.0:
                    self.status.value = "getting camera parameters"
                    status = self.pc.get_all_parameters()
                    temperatures = self.get_temperatures()
                    camera_parameters_last_updated = update_at

                    self.status.value = "updating status"
                    timestamp_comparison = self.pc.compare_timestamps()*1e6
                    status_update = dict(all_camera_parameters=status,
                                         camera_status_update_at=update_at,
                                         camera_timestamp_offset=timestamp_comparison,
                                         total_frames=frame_number,
                                         )
                    status_update.update(temperatures)
                    self.log_status(status_update)
                    self.pipeline.update_status(status_update)
                    self.counters.getting_parameters.increment()
                else:
                    time.sleep(0.001)
                    self.status.value = "waiting"
                    self.counters.waiting.increment()
        #if we get here, we were kindly asked to exit
        self.status.value = "exiting"
        if self.use_simulated_camera:
            self.pc._pc.quit()
        return None


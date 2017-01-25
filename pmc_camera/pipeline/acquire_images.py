import multiprocessing as mp
import os
import tempfile
import time
import logging
from Queue import Empty as EmptyException

logger = logging.getLogger(__name__)
import Pyro4
import numpy as np

Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.SERIALIZERS_ACCEPTED = {'pickle','json'}
Pyro4.config.SERIALIZER = 'pickle'


from pmc_camera.pycamera.dtypes import frame_info_dtype


LOG_DIR='/home/pmc/logs/housekeeping/camera'

class AcquireImagesProcess:
    def __init__(self, raw_image_buffers, acquire_image_output_queue, acquire_image_input_queue,
                 command_queue, command_result_queue, info_buffer,status,use_simulated_camera,uri):
        self.data_buffers = raw_image_buffers
        self.input_queue = acquire_image_input_queue
        self.output_queue = acquire_image_output_queue
        self.command_queue = command_queue
        self.command_result_queue = command_result_queue
        self.info_buffer = info_buffer
        self.use_simulated_camera = use_simulated_camera
        self.uri = uri
        self.status = status
        self.status.value="starting"
        self.child = mp.Process(target=self.run)
        #self.child.start()

    def create_log_file(self,log_dir=LOG_DIR):
        try:
            os.makedirs(log_dir)
        except OSError:
            pass

        self.temperature_log_filename = os.path.join(log_dir,(time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.temperature_log_file = open(self.temperature_log_filename,'a')

    def write_temperature_log(self):
        epoch = time.time()
        self.pc.set_parameter("DeviceTemperatureSelector","Main")
        main = self.pc.get_parameter("DeviceTemperature")
        self.pc.set_parameter("DeviceTemperatureSelector","Sensor")
        sensor = self.pc.get_parameter("DeviceTemperature")
        self.temperature_log_file.write("%f,%s,%s\n" % (epoch,main,sensor))
        self.temperature_log_file.flush()

    def run(self):
        self.pipeline = Pyro4.Proxy(uri=self.uri)
        self.pipeline._pyroTimeout = 0
        # Setup
        frame_number = 0
        import pmc_camera
        self.status.value = "initializing camera"
        self.pc = pmc_camera.PyCamera("10.0.0.2",use_simulated_camera=self.use_simulated_camera)
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

        if self.use_simulated_camera:
            log_dir = tempfile.mkdtemp("simulated_camera_logs")
        else:
            log_dir = LOG_DIR
        self.create_log_file(log_dir=log_dir)
        self.temperature_log_file.write('# %s %s %s %s\n' %
                                        (self.pc.get_parameter("DeviceModelName"),
                                         self.pc.get_parameter("DeviceID"),
                                         self.pc.get_parameter("DeviceFirmwareVersion"),
                                         self.pc.get_parameter("GevDeviceMACAddress")))
        self.temperature_log_file.write("epoch,sensor,main\n")

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
                    print "Errorcode while queueing buffer:",result
                else:
                    buffers_on_camera.add(ready_to_queue)
            if exit_request:
                break
            if time.time() > last_trigger + 0.5:
                gate_time = int(time.time()+1)
                if not self.command_queue.empty():
                    name,value,tag = self.command_queue.get()
                    self.status.value = "sending command"
                    if value is None:
                        result = self.pc.run_feature_command(name)
                    else:
                        result = self.pc.set_parameter(name,value)
                    gate_time = int(time.time()+1)  # update gate time in case some time has elapsed while executing
                    # command
                    self.command_result_queue.put((tag,name,value,result,gate_time))
                self.status.value = "arming camera"
                self.pc.set_parameter('PtpAcquisitionGateTime',str(int(gate_time*1e9)))
                time.sleep(0.1)
                self.pc.run_feature_command("AcquisitionStart")
                last_trigger = gate_time

            if not buffers_on_camera:
                self.status.value = "waiting for buffer on camera"
                time.sleep(0.001)
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
            if num_buffers_filled == 0:
                self.status.value = "waiting for buffer to be filled"
                update_at = time.time()
                if update_at - camera_parameters_last_updated > 1.0:
                    self.status.value = "getting camera parameters"
                    status = self.pc.get_all_parameters()
                    self.write_temperature_log()
                    camera_parameters_last_updated = update_at

                    self.status.value = "updating status"
                    timestamp_comparison = self.pc.compare_timestamps()*1e6
                    self.pipeline.update_status(dict(all_camera_parameters=status,
                                                camera_status_update_at=update_at,
                                                camera_timestamp_offset=timestamp_comparison,
                                                total_frames=frame_number,
                                                     ))
                else:
                    time.sleep(0.001)
                    self.status.value = "waiting"
        #if we get here, we were kindly asked to exit
        self.status.value = "exiting"
        if self.use_simulated_camera:
            self.pc._pc.quit()
        return None


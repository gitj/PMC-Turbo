"""
Basic pipeline to capture images perform processing, and save to disk.

Currently starts one thread (process) to capture images and 4 threads to write the images to disk.

Eventually want to add threads to do autofocus, autoexposure. Need to keep track of biger status and more camera
status too.

Example usage:

In [1]: import pmc_camera.pipeline.basic_pipeline

In [2]: bpl = pmc_camera.pipeline.basic_pipeline.BasicPipeline()

In [3]: bpl.get_status()
acquire: processing disk0:waiting disk1:processing disk2:waiting disk3:waiting

In [9]: bpl.close() # cleanly shutdown the threads to exit (otherwise ipython will hang)

"""
import numpy as np
import multiprocessing as mp
import time
import os
import sys
import ctypes
from Queue import Empty as EmptyException
import logging

import Pyro4, Pyro4.socketutil
import select
import signal

from pmc_camera.pycamera.dtypes import frame_info_dtype,chunk_dtype, chunk_num_bytes

index_file_name = 'index.csv'
index_file_header = ",".join(['file_index',
                              'write_timestamp',
                              'frame_timestamp_ns',
                              'frame_status',
                              'frame_id',
                              'acquisition_count',
                              'lens_status',
                              'focus_step',
                              'aperture_stop',
                              'exposure_us',
                              'gain_db',
                              'focal_length_mm',
                              'filename']) + '\n'

Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.SERIALIZERS_ACCEPTED = {'pickle','json'}
Pyro4.config.SERIALIZER = 'pickle'

logger = logging.getLogger(__name__)
LOG_DIR='/home/pmc/logs/housekeeping/camera'

@Pyro4.expose
class BasicPipeline:
    def __init__(self, dimensions=(3232,4864), num_data_buffers=16,
                 disks_to_use = ['/data1','/data2','/data3','/data4'],
                 use_simulated_camera=False, default_write_enable=1):
        image_size_bytes = 31440952 # dimensions[0]*dimensions[1]*2  # Need to figure out how to not hard code this
        self.num_data_buffers = num_data_buffers
        self.raw_image_buffers = [mp.Array(ctypes.c_uint8, image_size_bytes) for b in range(num_data_buffers)]
        # We save the buffer info in a custom datatype array, which is a bit ugly, but it works and isn't too bad.
        self.info_buffer = [mp.Array(ctypes.c_uint8, frame_info_dtype.itemsize)
                            for b in range(num_data_buffers)]

        # The input queue holds indexes for the buffers that have already been emptied (processed) and are ready to
        # recieve new images. The acquire thread grabs an index from the input queue, fills the corresponding buffer,
        # wirtes the info to the info_buffer and then puts that index into the output queue to indicate that that
        # buffer is ready for processing.
        #
        # Right now there is only one next step: writing to disk. So the disk thread uses the
        # acquire_image_output_queue as it's input (where it looks for the next buffer that needs processing). And
        # when it's done, it puts the index of the now empty buffer back in acquire_image_input queue so it can be
        # filled again.
        #
        # When we add another step, we'll need to make more queues (and maybe more buffers) to hand the data between
        # different processes
        self.acquire_image_input_queue = mp.Queue()
        self.acquire_image_output_queue = mp.Queue()
        self.acquire_image_command_queue = mp.Queue()
        self.acquire_image_command_results_queue = mp.Queue()
        self.acquire_image_command_results_dict = {}

        # The following are shared status variables used to indicate what state each process is in.
        # We can also use such things for other state (i.e. camera or birger state, or other housekeeping) if
        # desired, but that might unecessarily complicate things
        self.acquire_status = mp.Array(ctypes.c_char,32)
        self.disk_statuses = [mp.Array(ctypes.c_char,32) for disk in disks_to_use]
        num_writers = len(disks_to_use)

        self.disk_write_enables = [mp.Value(ctypes.c_int32) for disk in disks_to_use]
        for enable in self.disk_write_enables:
            enable.value=int(default_write_enable)

        # we prime the input queue to indicate that all buffers are ready to be filled
        for i in range(num_data_buffers):
            self.acquire_image_input_queue.put(i)

        self.status_dict = {}

        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip,port=50000)
        uri = self.daemon.register(self,"pipeline")
        print uri

        # instantiate (and start) the threads
        # in general, make sure to instantiate the Acquire process last; that way no data starts flowing through the
        # system until all threads have started running.
        output_dir = time.strftime("%Y-%m-%d_%H%M%S")
        self.writers = [WriteImageProcess(input_buffers=self.raw_image_buffers,
                                          input_queue=self.acquire_image_output_queue,
                                          output_queue = self.acquire_image_input_queue,
                                          info_buffer=self.info_buffer,dimensions=dimensions,
                                          status = self.disk_statuses[k],
                                          output_dir=output_dir,
                                          available_disks=[disks_to_use[k]],
                                          write_enable=self.disk_write_enables[k],
                                          uri=uri)
                        for k in range(num_writers)]

        self.acquire_images = AcquireImagesProcess(raw_image_buffers=self.raw_image_buffers,
                                                              acquire_image_output_queue=self.acquire_image_output_queue,
                                                              acquire_image_input_queue=self.acquire_image_input_queue,
                                                   command_queue=self.acquire_image_command_queue,
                                                   command_result_queue=self.acquire_image_command_results_queue,
                                                              info_buffer=self.info_buffer,
                                                   status=self.acquire_status,
                                                   use_simulated_camera=use_simulated_camera,
                                                   uri=uri)

        for writer in self.writers:
            writer.child.start()
        self.acquire_images.child.start()
        #signal.signal(signal.SIGTERM,self.exit)

    def run_pyro_loop(self):
        self.daemon.requestLoop()
    @Pyro4.oneway
    def update_status(self,d):
        self.status_dict.update(d)
    def _keep_running(self):
        print "check running",self.keep_running
        return self.keep_running
    def get_status(self):
        """
        return the status dictionary
        Returns
        -------

        """
        process_status = dict(acquire=self.acquire_status.value)
        for k,status in enumerate(self.disk_statuses):
            process_status['disk %d' % k] = status.value
            process_status['disk write enable %d' %k] = self.disk_write_enables[k].value

        self.status_dict.update(process_status)
        return self.status_dict

    def send_camera_command(self,name,value):
        tag = time.time()
        self.acquire_image_command_queue.put((name,value,tag))
        return tag

    def get_camera_command_result(self,command_tag):
        while not self.acquire_image_command_results_queue.empty():
            try:
                tag,name,value,result = self.acquire_image_command_results_queue.get_nowait()
                self.acquire_image_command_results_dict[tag] = (name,value,result)
            except EmptyException:
                break
        if command_tag in self.acquire_image_command_results_dict:
            return self.acquire_image_command_results_dict.pop(command_tag)
        else:
            raise KeyError("Result of command tag %r not found" % command_tag)

    def send_camera_command_get_result(self,name,value,timeout=1):
        tag = self.send_camera_command(name,value)
        start = time.time()
        while time.time() - start < timeout:
            try:
                return self.get_camera_command_result(tag)
            except KeyError:
                time.sleep(0.01)
        raise RuntimeError("Timeout waiting for command result")


    @Pyro4.oneway
    def close(self):
        """
        Request all processing threads to stop.

        Right now this is accomplished by putting None into the queues which acts as a kill request. probably better
        to use a shared variable to request threads to die.
        Returns
        -------

        """
        self.acquire_image_input_queue.put(None)
        for k in range(8):
            self.acquire_image_output_queue.put(None)
        self.acquire_images.child.join()
        #self.write_images.child.join()
        for writer in self.writers:
            writer.child.join()
        self.daemon.shutdown()
    def exit(self,signum,frame):
        print "exiting with signum",signum,frame
        self.close()
        sys.exit(0)

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

        self.temperature_log_filename = os.path.join(LOG_DIR,(time.strftime('%Y-%m-%d_%H%M%S.csv')))
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

        self.create_log_file()
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

        last_camera_status = {}

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
                if not self.command_queue.empty():
                    name,value,tag = self.command_queue.get()
                    self.status.value = "sending command"
                    if value is None:
                        result = self.pc.run_feature_command(name)
                    else:
                        result = self.pc.set_parameter(name,value)
                    self.command_result_queue.put((tag,name,value,result))
                self.status.value = "arming camera"
                start_time = int(time.time()+1)
                self.pc.set_parameter('PtpAcquisitionGateTime',str(int(start_time*1e9)))
                time.sleep(0.1)
                self.pc.run_feature_command("AcquisitionStart")
                last_trigger = start_time

            if not buffers_on_camera:
                time.sleep(0.001)
            num_buffers_filled = 0
            for buffer_id in list(buffers_on_camera):
                npy_info_buffer = np.frombuffer(self.info_buffer[buffer_id].get_obj(),dtype=frame_info_dtype)
                if npy_info_buffer[0]['is_filled']:
                    self.status.value = 'buffer %d was filled by camera' % buffer_id
                    self.output_queue.put(buffer_id)
                    buffers_on_camera.remove(buffer_id)
                    frame_number += 1
                    num_buffers_filled +=1
            if num_buffers_filled == 0:
                update_at = time.time()
                if update_at - camera_parameters_last_updated > 1.0:
                    status = self.pc.get_all_parameters()
                    self.write_temperature_log()
                    camera_parameters_last_updated = update_at
                    last_camera_status = status
                else:
                    status = last_camera_status
                timestamp_comparison = self.pc.compare_timestamps()*1e6
                self.pipeline.update_status(dict(all_camera_parameters=status,
                                            camera_status_update_at=update_at,
                                            camera_timestamp_offset=timestamp_comparison,
                                            total_frames=frame_number,
                                                 ))
        #if we get here, we were kindly asked to exit
        self.status.value = "exiting"
        return None

class WriteImageProcess(object):
    def __init__(self,input_buffers, input_queue, output_queue, info_buffer, dimensions, status, output_dir,
                 available_disks, write_enable, uri):
        self.data_buffers = input_buffers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.info_buffer = info_buffer
        self.available_disks = available_disks
        self.dimensions=dimensions
        self.write_enable = write_enable
        self.uri = uri
        self.output_dirs = [os.path.join(rpath,output_dir) for rpath in available_disks]
        for dname in self.output_dirs:
            try:
                os.mkdir(dname)
            except OSError:
                pass
        self.disk_to_use = 0
        self.status = status
        self.status.value = "starting"
        self.child = mp.Process(target=self.run)
        #self.child.start()

    def run(self):
        process_me = -1
        frame_indexes = dict([(dirname,0) for dirname in self.output_dirs])
        for dirname in self.output_dirs:
            with open(os.path.join(dirname,index_file_name),'w') as fh:
                fh.write(index_file_header)
        while True:
            try:
                process_me = self.input_queue.get_nowait()
            except EmptyException:
                self.status.value = "waiting"
                time.sleep(0.005)
                continue
            if process_me is None:
                break
            else:
                with self.data_buffers[process_me].get_lock():
                    self.status.value = "processing %d" % process_me
                    #t0 = timeit.default_timer()
                    image_buffer = np.frombuffer(self.data_buffers[process_me].get_obj(), dtype='uint16')
                    #image_buffer.shape=self.dimensions
                    npy_info_buffer = np.frombuffer(self.info_buffer[process_me].get_obj(),dtype=frame_info_dtype)
                    info = dict([(k,npy_info_buffer[0][k]) for k in frame_info_dtype.fields.keys()])
                    chunk_data = image_buffer.view('uint8')[-chunk_num_bytes:].view(chunk_dtype)[0]
                    ts = time.strftime("%Y-%m-%d_%H%M%S")
                    info_str = '_'.join([('%s=%r' % (k,v)) for (k,v) in info.items()])
                    #print process_me, self.available_disks[self.disk_to_use], info['frame_id'], info['size']#, info_str
                    ts = ts + '_' + info_str
                    dirname = self.output_dirs[self.disk_to_use]
                    fname = os.path.join(dirname,ts)
                    #'file_index,write_timestamp,frame_timestamp_ns,frame_status,frame_id,acquisition_count,lens_status,
                    # focus_step,aperture_stop,exposure_us,gain_db,focal_length_mm,filename'
                    lens_status = chunk_data['lens_status_focus'] >> 10
                    focus_step = chunk_data['lens_status_focus'] & 0x3FF
                    if self.write_enable.value:
                        write_image_blosc(fname,image_buffer) # fast and good lossless compression
                        with open(os.path.join(dirname,index_file_name),'a') as fh:
                            fh.write('%d,%f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s\n' %
                                     (frame_indexes[dirname],
                                      time.time(),
                                      info['timestamp'],
                                      info['frame_status'],
                                      info['frame_id'],
                                      chunk_data['acquisition_count'],
                                      lens_status,
                                      focus_step,
                                      chunk_data['lens_aperture'],
                                      chunk_data['exposure_us'],
                                      chunk_data['gain_db'],
                                      chunk_data['lens_focal_length'],
                                      fname
                                      ))
                    self.disk_to_use = (self.disk_to_use + 1) % len(self.output_dirs) # if this thread is cycling
                    frame_indexes[dirname] = frame_indexes[dirname] + 1
                    # between disks, do the cycling here.
                    self.output_queue.put(process_me)

        self.status.value = "exiting"
        return None

import netCDF4

def write_image_to_netcdf(filename,data):
    ds = netCDF4.Dataset(filename,mode='w')
    dimx = ds.createDimension('x',size=data.shape[0])
    dimy = ds.createDimension('y',size=data.shape[1])
    var = ds.createVariable('image',dimensions=('x','y'),datatype=data.dtype,zlib=True,complevel=1)#,contiguous=True)
    var[:] = data[:]
    ds.sync()
    ds.close()

import blosc
def write_image_blosc(filename,data):
    fh = open(filename,'wb')
    fh.write(blosc.compress(data,shuffle=blosc.BITSHUFFLE,cname='lz4'))
    fh.close()
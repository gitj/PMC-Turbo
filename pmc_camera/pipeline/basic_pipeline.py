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
import ctypes
from Queue import Empty as EmptyException

from pmc_camera.pycamera.pycamera import frame_info_dtype

class BasicPipeline:
    def __init__(self, dimensions=(3232,4864), num_data_buffers=16,
                 disks_to_use = ['/data1','/data2','/data3','/data4']):
        image_size_bytes = dimensions[0]*dimensions[1]*2
        self.num_data_buffers = num_data_buffers
        self.raw_image_buffers = [mp.Array(ctypes.c_uint8, image_size_bytes) for b in range(num_data_buffers)]
        # We save the buffer info in a custom datatype array, which is a bit ugly, but it works and isn't too bad.
        self.info_buffer = [mp.Array(ctypes.c_uint8, frame_info_dtype.itemsize) for b in range(
            num_data_buffers)]

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

        # The following are shared status variables used to indicate what state each process is in.
        # We can also use such things for other state (i.e. camera or birger state, or other housekeeping) if
        # desired, but that might unecessarily complicate things
        self.acquire_status = mp.Array(ctypes.c_char,32)
        self.disk_statuses = [mp.Array(ctypes.c_char,32) for disk in disks_to_use]
        num_writers = len(disks_to_use)

        # we prime the input queue to indicate that all buffers are ready to be filled
        for i in range(num_data_buffers):
            self.acquire_image_input_queue.put(i)

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
                                          available_disks=[disks_to_use[k]])
                        for k in range(num_writers)]

        self.acquire_images = AcquireImagesProcess(raw_image_buffers=self.raw_image_buffers,
                                                              acquire_image_output_queue=self.acquire_image_output_queue,
                                                              acquire_image_input_queue=self.acquire_image_input_queue,
                                                              info_buffer=self.info_buffer,dimensions=dimensions,
                                                   status=self.acquire_status)



    def get_status(self):
        """
        Print the status of all processing threads
        Returns
        -------

        """
        disk_status = ' '.join([('disk%d:%s' % (k,status.value)) for k,status in enumerate(self.disk_statuses)])
        print "acquire:",self.acquire_status.value, disk_status

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


class AcquireImagesProcess:
    def __init__(self, raw_image_buffers, acquire_image_output_queue, acquire_image_input_queue, info_buffer,
                 dimensions,status):
        self.data_buffers = raw_image_buffers
        self.input_queue = acquire_image_input_queue
        self.output_queue = acquire_image_output_queue
        self.info_buffer = info_buffer
        self.status = status
        self.status.value="starting"
        self.child = mp.Process(target=self.run)
        self.child.start()

    def run(self):
        # Setup
        frame_number = 0
        import pmc_camera
        self.status.value = "initializing camera"
        self.pc = pmc_camera.PyCamera("10.0.0.2")
        self.pc._pc.start_capture()
        self.pc._pc.set_parameter_from_string("AcquisitionFrameCount","2")
        self.pc._pc.set_parameter_from_string('AcquisitionMode',"MultiFrame")
        self.pc._pc.set_parameter_from_string('AcquisitionFrameRateAbs',"6.25")
        self.pc._pc.set_parameter_from_string('TriggerSource','FixedRate')
        self.pc._pc.set_parameter_from_string('ExposureTimeAbs',"100000")

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
                self.status.value = "arming camera"
                start_time = int(time.time()+1)
                self.pc._pc.set_parameter_from_string('PtpAcquisitionGateTime',str(int(start_time*1e9)))
                self.pc._pc.run_feature_command("AcquisitionStart")
                last_trigger = start_time

            if not buffers_on_camera:
                time.sleep(0.001)
            for buffer_id in list(buffers_on_camera):
                npy_info_buffer = np.frombuffer(self.info_buffer[buffer_id].get_obj(),dtype=frame_info_dtype)
                if npy_info_buffer[0]['is_filled']:
                    self.status.value = 'buffer %d was filled by camera' % buffer_id
                    self.output_queue.put(buffer_id)
                    buffers_on_camera.remove(buffer_id)
                    frame_number += 1
        #if we get here, we were kindly asked to exit
        self.status.value = "exiting"
        return None

class WriteImageProcess(object):
    def __init__(self,input_buffers, input_queue, output_queue, info_buffer, dimensions, status, output_dir,
                 available_disks = ['/data1', '/data2', '/data3', '/data4']):
        self.data_buffers = input_buffers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.info_buffer = info_buffer
        self.available_disks = available_disks
        self.dimensions=dimensions
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
        self.child.start()

    def run(self):
        process_me = -1
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
                    image_buffer.shape=self.dimensions
                    npy_info_buffer = np.frombuffer(self.info_buffer[process_me].get_obj(),dtype=frame_info_dtype)
                    info = dict([(k,npy_info_buffer[0][k]) for k in frame_info_dtype.fields.keys()])
                    ts = time.strftime("%Y-%m-%d_%H%M%S")
                    info_str = '_'.join([('%s=%r' % (k,v)) for (k,v) in info.items()])
                    #print process_me, self.available_disks[self.disk_to_use], info['frame_id'], info['size']#, info_str
                    ts = ts + '_' + info_str
                    fname = os.path.join(self.output_dirs[self.disk_to_use],ts)
                    #np.savez(fname,info=info,image=image_buffer) # too slow
                    #image_buffer.tofile(fname) # very fast but just raw binary, no compression, no metadata
                    #write_image_to_netcdf(fname,image_buffer) # works nicely, but compression is not quite as good as
                    # blosc. May be preferable since metadata is kept nicely.
                    write_image_blosc(fname,image_buffer) # fast and good lossless compression
                    self.disk_to_use = (self.disk_to_use + 1) % len(self.output_dirs) # if this thread is cycling
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
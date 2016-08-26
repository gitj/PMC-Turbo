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

import pmc_camera

info_dtype = np.dtype([('block_id', 'uint64'),
                       ('buffer_id', 'uint64'),
                       ('operation_code', 'uint32'),
                       ('result_code', 'uint32'),
                       ('reception_time', 'uint64'),
                       ('timestamp', 'uint64'),
                       ('size', 'uint32'),
                       ('acquisition_start_time', 'float64')
                       ])
class BasicPipeline:
    def __init__(self, dimensions=(3232,4864), num_data_buffers=16,
                 disks_to_use = ['/data1','/data2','/data3','/data4']):
        image_size_bytes = dimensions[0]*dimensions[1]*2
        self.num_data_buffers = num_data_buffers
        self.raw_image_buffers = [mp.Array(ctypes.c_uint8, image_size_bytes) for b in range(num_data_buffers)]
        # We save the buffer info in a custom datatype array, which is a bit ugly, but it works and isn't too bad.
        self.info_buffer = mp.Array(ctypes.c_uint8, info_dtype.itemsize * num_data_buffers)

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

        self.writers = [WriteImageProcess(input_buffers=self.raw_image_buffers,
                                              input_queue=self.acquire_image_output_queue,
                                              output_queue = self.acquire_image_input_queue,
                                              info_buffer=self.info_buffer,dimensions=dimensions,
                                              status = self.disk_statuses[k],available_disks=[disks_to_use[k]])
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
        self.pc = pmc_camera.PyCamera("10.0.0.2")
        self.acquisition_start_time = time.time()
        # Run loop
        while True:
            info = None
            try:
                # check for an available buffer to fill. If this fails, data is coming in too fast for us to keep up
                # or there is a bug causing later stages to not release buffers back to the input queue
                process_me = self.input_queue.get_nowait()
            except EmptyException:
                # if we're here, no buffer is currently available so we have no choice but to sit and wait for one to
                #  become available. We could lose data during this time.
                self.status.value = "blocked"
                time.sleep(0.005)
                continue
            if process_me is None:
                # if someone put None in the queue, it means they want all threads to quit nicely
                break
            else:
                #here we are with a valid buffer. We first grab the lock to the buffer since we;ll be writing into
                # it. This should never block since no one else is writing to it at this time, but just in case.
                with self.data_buffers[process_me].get_lock():
                    self.status.value = "processing"
                    # cast the current buffer to a numpy array
                    image_buffer = np.frombuffer(self.data_buffers[process_me].get_obj(), dtype='uint8')
                    # load an image from the camera into the array
                    info = self.pc.get_image_into_buffer(image_buffer)
                    # FIXME: this is just for quick debugging
                    if info['size'] == 0 or info['operation_code'] or info['result_code']:
                        print info
                    #cast the buffer array using the compound data type that has a spot for each info field
                    npy_info_buffer = np.frombuffer(self.info_buffer.get_obj(),dtype=info_dtype)
                    #and load the info into the appropriate location
                    for k,v in info.items():
                        npy_info_buffer[process_me][k] = v
                    npy_info_buffer[process_me]['acquisition_start_time'] = self.acquisition_start_time
                # now we are done with the buffer so we pass it on to the next thread
                self.output_queue.put(process_me)
        #if we get here, we were kindly asked to exit
        self.status.value = "exiting"
        return None

class WriteImageProcess(object):
    def __init__(self,input_buffers, input_queue, output_queue, info_buffer, dimensions, status,
                 available_disks = ['/data1', '/data2', '/data3', '/data4']):
        self.data_buffers = input_buffers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.info_buffer = info_buffer
        self.available_disks = available_disks
        self.dimensions=dimensions
        ts = time.strftime("%Y-%m-%d_%H%M%S")
        self.output_dirs = [os.path.join(rpath,ts) for rpath in available_disks]
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
                    self.status.value = "processing"
                    #t0 = timeit.default_timer()
                    image_buffer = np.frombuffer(self.data_buffers[process_me].get_obj(), dtype='uint16')
                    image_buffer.shape=self.dimensions
                    npy_info_buffer = np.frombuffer(self.info_buffer.get_obj(),dtype=info_dtype)
                    info = dict([(k,npy_info_buffer[process_me][k]) for k in info_dtype.fields.keys()])
                    ts = time.strftime("%Y-%m-%d_%H%M%S")
                    info_str = '_'.join([('%s=%r' % (k,v)) for (k,v) in info.items()])
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
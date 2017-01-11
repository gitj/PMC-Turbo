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
import ctypes
import logging
import multiprocessing as mp
import sys
import time
from Queue import Empty as EmptyException

import Pyro4
import Pyro4.socketutil

from pmc_camera.pipeline.acquire_images import AcquireImagesProcess
from pmc_camera.pipeline.write_images import WriteImageProcess
from pmc_camera.pycamera.dtypes import frame_info_dtype

Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.SERIALIZERS_ACCEPTED = {'pickle','json'}
Pyro4.config.SERIALIZER = 'pickle'

logger = logging.getLogger(__name__)


@Pyro4.expose
class BasicPipeline:
    def __init__(self, dimensions=(3232,4864), num_data_buffers=16,
                 disks_to_use = ['/data1','/data2','/data3','/data4'],
                 use_simulated_camera=False, default_write_enable=1, pipeline_port=50000):
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
        self.daemon = Pyro4.Daemon(host='0.0.0.0',port=pipeline_port)
        uri = self.daemon.register(self,"pipeline")
        print uri

        # instantiate (and start) the threads
        # in general, make sure to instantiate the Acquire process last; that way no data starts flowing through the
        # system until all threads have started running.
        output_dir = time.strftime("%Y-%m-%d_%H%M%S")
        self.writers = [
            WriteImageProcess(input_buffers=self.raw_image_buffers, input_queue=self.acquire_image_output_queue,
                              output_queue=self.acquire_image_input_queue, info_buffer=self.info_buffer,
                              dimensions=dimensions, status=self.disk_statuses[k], output_dir=output_dir,
                              available_disks=[disks_to_use[k]], write_enable=self.disk_write_enables[k])
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
        self.update_command_results()
        if command_tag in self.acquire_image_command_results_dict:
            return self.acquire_image_command_results_dict.pop(command_tag)
        else:
            raise KeyError("Result of command tag %r not found" % command_tag)

    def update_command_results(self):
        while not self.acquire_image_command_results_queue.empty():
            try:
                tag,name,value,result,gate_time = self.acquire_image_command_results_queue.get_nowait()
                self.acquire_image_command_results_dict[tag] = (name,value,result,gate_time)
            except EmptyException:
                break

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
        self.acquire_images.child.join(timeout=1)
        logger.debug("acquire process status at exit: %s" % self.acquire_status.value)
        #self.write_images.child.join()
        for k,writer in enumerate(self.writers):
            writer.child.join(timeout=1)
            logger.debug("writer process status at exit: %s" % self.disk_statuses[k].value)
            writer.child.terminate()
        self.acquire_images.child.terminate()
        self.daemon.shutdown()
    def exit(self,signum,frame):
        print "exiting with signum",signum,frame
        self.close()
        sys.exit(0)

# import netCDF4
#
# def write_image_to_netcdf(filename,data):
#     ds = netCDF4.Dataset(filename,mode='w')
#     dimx = ds.createDimension('x',size=data.shape[0])
#     dimy = ds.createDimension('y',size=data.shape[1])
#     var = ds.createVariable('image',dimensions=('x','y'),datatype=data.dtype,zlib=True,complevel=1)#,contiguous=True)
#     var[:] = data[:]
#     ds.sync()
#     ds.close()


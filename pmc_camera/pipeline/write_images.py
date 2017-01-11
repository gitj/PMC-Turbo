import multiprocessing as mp
import os
import time
import logging
from Queue import Empty as EmptyException

logger = logging.getLogger(__name__)


import numpy as np

from pmc_camera.image_processing.blosc_file import write_image_blosc
from pmc_camera.pycamera.dtypes import frame_info_dtype, chunk_num_bytes, chunk_dtype

index_file_name = 'index.csv'
index_keys = ['file_index',
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
              'filename']
index_file_header = ",".join(index_keys) + '\n'

DISK_MIN_BYTES_AVAILABLE = 100*1024*1024 # 100 MiB



class WriteImageProcess(object):
    def __init__(self, input_buffers, input_queue, output_queue, info_buffer, dimensions, status, output_dir,
                 available_disks, write_enable):
        self.data_buffers = input_buffers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.info_buffer = info_buffer
        self.original_disks = available_disks
        disks_with_free_space = []
        for disk in available_disks:
            stats = os.statvfs(disk)
            bytes_available = stats.f_bavail*stats.f_frsize
            if bytes_available > DISK_MIN_BYTES_AVAILABLE:
                disks_with_free_space.append(disk)
            else:
                logger.warning("Insufficient disk space available on %s, only %d MiB" % (disk,bytes_available//2**20))
        self.available_disks = disks_with_free_space
        self.dimensions=dimensions
        self.write_enable = write_enable
        self.output_dirs = [os.path.join(rpath,output_dir) for rpath in self.available_disks]
        for dname in self.output_dirs:
            try:
                os.mkdir(dname)
            except OSError:
                logger.exception("Error creating data directory %s" % dname)
        self.disk_to_use = 0
        self.status = status
        if self.output_dirs:
            self.status.value = "starting"
        else:
            self.status.value = "no disk space"
            self.write_enable.value = False
        self.child = mp.Process(target=self.run)

    def run(self):
        if not self.available_disks:
            logger.warning("No disk space available on any of %s, exiting" % (' '.join(self.original_disks)))
            return
        frame_indexes = dict([(dirname,0) for dirname in self.output_dirs])
        for dirname in self.output_dirs:
            with open(os.path.join(dirname,index_file_name),'w') as fh:
                fh.write(index_file_header)
        while True:
            try:
                process_me = self.input_queue.get_nowait()
            except EmptyException:
                self.status.value = "waiting"
                time.sleep(0.1)
                continue
            if process_me is None:
                self.status.value = "exiting"
                logger.info("Exiting normally")
                break
            else:
                self.status.value = "checking disk"
                available_output_dirs = []
                for output_dir in self.output_dirs:
                    stats = os.statvfs(output_dir)
                    bytes_available = stats.f_bavail*stats.f_frsize
                    if bytes_available > DISK_MIN_BYTES_AVAILABLE:
                        available_output_dirs.append(output_dir)
                    else:
                        logger.warning("Insufficient disk space available on %s, only %d MiB" %
                                       (output_dir,bytes_available//2**20))
                self.output_dirs = available_output_dirs
                if not self.output_dirs:
                    self.status.value = "no disk space"
                    logger.warning("No disk space available on any of %s, exiting" % (' '.join(self.original_disks)))
                    break
                if self.disk_to_use >= len(self.output_dirs):
                    self.disk_to_use = 0
                self.status.value = "waiting for lock"
                with self.data_buffers[process_me].get_lock():
                    self.status.value = "processing %d" % process_me
                    logger.debug(self.status.value)
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
                        self.status.value = "writing %d" % process_me
                        write_image_blosc(fname, image_buffer)
#                        self.status.value = "writing %d metadata" % process_me
                        with open(os.path.join(dirname,index_file_name),'a') as fh:
                            #  self.status.value = "index file opened"
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
                    self.status.value = "finishing %d" % process_me
                    self.output_queue.put(process_me)

        self.status.value = "exiting"
        return None



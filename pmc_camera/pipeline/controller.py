import glob
import logging
import os
import time
from functools import wraps

import Pyro4

from pmc_camera.communication import file_format_classes
from pmc_camera.image_processing.blosc_file import load_blosc_image
from pmc_camera.image_processing.jpeg import simple_jpeg
from pmc_camera.pipeline.indexer import MergedIndex, DEFAULT_DATA_DIRS
from pmc_camera.pipeline.write_images import index_keys
from pmc_camera.utils.camera_id import get_camera_id

logger = logging.getLogger(__name__)

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]

DEFAULT_REQUEST_ID = 2**32-1


class ImageParameters(object):
    pass

def require_pipeline(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        self = args[0]
        if self.pipeline is None:
            return None
        else:
            return func(*args,**kwargs)
    return wrapper


@Pyro4.expose
class Controller(object):
    def __init__(self, pipeline, data_dirs=DEFAULT_DATA_DIRS, gate_time_error_threshold=2e-3):
        self.data_dirs = data_dirs
        self.pipeline = pipeline
        self.gate_time_error_threshold = gate_time_error_threshold
        self.latest_image_subdir = ''
        self.merged_index = None
        self.sequence_data = []
        self.outstanding_command_tags = {}
        self.completed_command_tags = {}
        self.camera_id = get_camera_id()
        self.update_current_image_dirs()
        self.set_standard_image_paramters()


    @require_pipeline
    def set_focus(self,focus_step):
        tag = self.pipeline.send_camera_command("EFLensFocusCurrent",str(focus_step))
        return tag

    @require_pipeline
    def set_exposure(self,exposure_time_us):
        tag = self.pipeline.send_camera_command("ExposureTimeAbs",str(exposure_time_us))
        return tag

    @require_pipeline
    def run_focus_sweep(self,request_params,start=1950,stop=2150,step=10):
        focus_steps = range(start,stop,step)
        tags = [self.set_focus(focus_step) for focus_step in focus_steps]
        for tag in tags:
            self.outstanding_command_tags[tag] = request_params

    @require_pipeline
    def check_for_completed_commands(self):
        for tag in self.outstanding_command_tags.keys():
            try:
                name,value,result,gate_time = self.pipeline.get_camera_command_result(tag)
                logger.debug("Command %s:%s completed with gate_time %f" % (name,value,gate_time))
                self.completed_command_tags[tag] = (name,value,result,gate_time)
            except KeyError:
                pass

        for tag in self.completed_command_tags.keys():
            name,value,result,gate_time = self.completed_command_tags[tag]
            index = self.merged_index.get_index_of_timestamp(gate_time)
            if index is None:
                logger.warning("No index available, is the pipeline writing? Looking for gate_time %d" % gate_time)
                continue
            if index == len(self.merged_index.df):
                logger.info("Command tag %f - %s:%s complete, but image data not yet available" % (tag,name,value))
                continue
            row = self.merged_index.df.iloc[index]
            timestamp = row.frame_timestamp_ns/1e9
            if abs(gate_time-timestamp) < self.gate_time_error_threshold:
                request_params = self.outstanding_command_tags.pop(tag)
                _ = self.completed_command_tags.pop(tag)
                logger.info("Command tag %f - %s:%s retired" % (tag,name,value))
                logger.debug("Command %s:%s with request_params %r retired by image %r" %(name,value,
                                                                                         request_params,dict(row)))
                self.request_image_by_index(index,**request_params)
            else:
                logger.warning("Command tag %f - %s:%s complete, but image timestamp %f does not match "
                               "gate_timestamp %f to within specified threshold %f. Is something wrong with PTP?"
                               % (tag,name,value,gate_time,timestamp,self.gate_time_error_threshold))

    def update_current_image_dirs(self):
        all_dirs = []
        for data_dir in self.data_dirs:
            image_dirs = [os.path.split(x)[1] for x in glob.glob(os.path.join(data_dir, '20*'))]
            all_dirs.extend(image_dirs)
        all_dirs = list(set(all_dirs))  # get just the unique names
        all_dirs.sort()
        logger.debug("Found these dirs: %r" % all_dirs)
        try:
            latest = all_dirs[-1]
        except IndexError:
            logger.warning("No data directories found under %r" % self.data_dirs)
            self.merged_index = None
            self.latest_image_subdir =''
            return
        logger.debug("latest: %r" % latest)
        if latest != self.latest_image_subdir:
            logger.info("Found new image directory %s" % latest)
            self.latest_image_subdir = latest
            self.merged_index = MergedIndex(self.latest_image_subdir,data_dirs=self.data_dirs)

    def get_latest_fileinfo(self):
        if self.merged_index is None:
            self.update_current_image_dirs()
        if self.merged_index is not None:
            result = self.merged_index.get_latest()
            if result is None:
                raise RuntimeError("No candidates for latest file!")
            else:
                return result
        else:
            raise RuntimeError("No candidates for latest file!")

    def get_latest_standard_image(self):
        params = self.standard_image_parameters.copy()
        file_obj = self.get_latest_jpeg(**params)
        return file_obj

    def get_latest_jpeg(self, request_id, row_offset=0, column_offset=0, num_rows=3232, num_columns=4864, scale_by=1 /
                                                                                                                 8., **kwargs):
        info = self.get_latest_fileinfo()
        return self.get_image_by_info(info, request_id=request_id, row_offset=row_offset, column_offset=column_offset,
                                      num_rows=num_rows, num_columns=num_columns, scale_by=scale_by,
                                      **kwargs)

    def set_standard_image_paramters(self, row_offset=0, column_offset=0, num_rows=3232, num_columns=4864, scale_by=1 / 8., quality=75,
                                     format='jpeg'):
        self.standard_image_parameters = dict(row_offset=row_offset, column_offset=column_offset,
                                              num_rows=num_rows, num_columns=num_columns,
                                              scale_by=scale_by,
                                              quality=quality,
                                              format=format, request_id=DEFAULT_REQUEST_ID)

    def request_image_by_index(self,index,**kwargs):
        """

        Parameters
        ----------
        index

        Required kwargs
        ---------------
        request_id

        """
        self.merged_index.update()
        index_row_data =dict(self.merged_index.df.iloc[index])
        self.sequence_data.append(self.get_image_by_info(index_row_data,**kwargs).to_buffer())

    def request_specific_images(self, timestamp, request_id, num_images=1, row_offset=0, column_offset=0,
                                num_rows=3232, num_columns=4864, scale_by=1 / 8.,
                                quality=75,
                                format='jpeg', step=-1):
        last_index = self.merged_index.get_index_of_timestamp(timestamp)
        first_index = last_index + step * num_images
        logger.debug("request timestamp %f, num_images %d, step %d -> first index: %d, last index: %d, total rows: %d"
                     % (timestamp, num_images, step, first_index, last_index, self.merged_index.df.shape[0]))
        if first_index > last_index:
            first_index, last_index = last_index, first_index
        selection = self.merged_index.df.iloc[first_index, last_index, abs(step)]
        logger.debug("selected %d rows" % selection.shape[0])
        for _, index_row in selection.iterrows():
            self.sequence_data.append(self.get_image_by_info(index_row, row_offset=row_offset,
                                                             column_offset=column_offset,
                                                             num_rows=num_rows, num_columns=num_columns,
                                                             scale_by=scale_by, quality=quality, format=format,
                                                             request_id=request_id).to_buffer())

    def get_image_by_info(self, index_row_data, request_id, row_offset=0, column_offset=0, num_rows=3232,
                          num_columns=4864, scale_by=1 / 8., quality=75, format='jpeg'):
        image, chunk = load_blosc_image(index_row_data['filename'])
        image = image[row_offset:row_offset + num_rows + 1, column_offset:column_offset + num_columns + 1]
        params = dict()
        for key in index_keys:
            if key =='filename':
                continue
            params[key] = index_row_data[key]
        params['camera_id'] = self.camera_id
        params['request_id'] = request_id
        params['row_offset'] = row_offset
        params['column_offset'] = column_offset
        params['num_rows'] = num_rows
        params['num_columns'] = num_columns
        params['scale_by'] = scale_by
        params['quality'] = quality
        if format == 'jpeg':
            payload = simple_jpeg(image, scale_by=scale_by, quality=quality)
            file_obj = file_format_classes.JPEGFile(payload=payload,**params)
        else:
            raise ValueError("Unsupported format requested %r" % format)
        return file_obj


    def request_specific_file(self, filename, max_num_bytes, request_id):
        #TODO: What do do when file doesn't exist. Special error file type?
        timestamp = time.time()
        try:
            with open(filename, 'r') as fh:
                if max_num_bytes < 0:
                    fh.seek(max_num_bytes, os.SEEK_END)
                data = fh.read(max_num_bytes)
        except IOError as e:
            data = repr(e)
        file_object = file_format_classes.GeneralFile(payload=data,
                                                      timestamp=timestamp,
                                                      request_id=request_id,
                                                      filename=filename,
                                                      camera_id=self.camera_id)
        self.sequence_data.append(file_object.to_buffer())

    def get_next_data_for_downlink(self):
        #TODO: this should return a data buffer ready to downlink
        if self.sequence_data:
            result = self.sequence_data[0]
            self.sequence_data = self.sequence_data[1:]
        else:
            result = self.get_latest_standard_image().to_buffer()
        return result


if __name__ == "__main__":
    from pmc_camera.utils import log
    log.setup_stream_handler(level=logging.DEBUG)
    ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:50000' % ip)
    except Exception as e:
        print "failed to connect to pipeline:",e
        pipeline = None
    server = Controller(pipeline)
    ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
    daemon = Pyro4.Daemon(host='0.0.0.0', port=50001)
    uri = daemon.register(server, "image")
    print uri
    daemon.requestLoop()

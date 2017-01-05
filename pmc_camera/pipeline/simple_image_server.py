import glob
import os
import time
from functools import wraps

import PIL
import Pyro4
import logging
import pandas as pd

from pmc_camera.image_processing.jpeg import simple_jpeg
from pmc_camera.image_processing.blosc_file import load_blosc_image
from pmc_camera.utils.camera_id import get_camera_id
from pmc_camera.communication import file_format_classes

logger = logging.getLogger(__name__)

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]

DEFAULT_DATA_DIRS = ['/data1', '/data2', '/data3', '/data4']
INDEX_FILENAME = 'index.csv'


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
class SimpleImageServer(object):
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
                self.request_image_by_index(index,request_params)
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
        latest = all_dirs[-1]
        if latest != self.latest_image_subdir:
            logger.info("Found new image directory %s" % latest)
            self.latest_image_subdir = latest
            self.merged_index = MergedIndex(self.latest_image_subdir)

    def get_latest_fileinfo(self):
        if self.merged_index is None:
            self.update_current_image_dirs()
        if self.merged_index is not None:
            return self.merged_index.get_latest()
        else:
            raise RuntimeError("No candidates for latest file!")

    def get_latest_jpeg(self, offset=(0, 0), size=(3232, 4864), scale_by=1 / 8., **kwargs):
        info = self.get_latest_fileinfo()
        return self.get_image_by_info(info, offset=offset, size=size, scale_by=scale_by,
                                     format='jpeg', **kwargs)

    def request_image_by_index(self,index,request_params):
        request_params.update(dict(self.merged_index.df.iloc[index]))
        self.sequence_data.append(self.get_image_by_info(request_params))

    def get_image_by_info(self, request_params, offset=(0, 0), size=(3232, 4864), scale_by=1 / 8.,**kwargs):
        request_params['camera_id'] = self.camera_id
        image, chunk = load_blosc_image(request_params['filename'])
        row0, col0 = offset
        nrow, ncol = size
        image = image[row0:row0 + nrow + 1, col0:col0 + ncol + 1]
        params = dict(request_params)
        params['offset'] = offset
        params['size'] = size
        params['scale_by'] = scale_by
        params['file_type'] = file_format_classes.JPEGFile.file_type  # fixed to JPEG for now
        return simple_jpeg(image, scale_by=scale_by, **kwargs), params

    def set_standard_image_paramters(self, offset=(0, 0), size=(3232, 4864), scale_by=1 / 8., quality=75,
                                     format='jpeg'):
        self.standard_image_parameters = dict(offset=offset,
                                              size=size,
                                              scale_by=scale_by,
                                              quality=quality,
                                              format=format)

    def get_latest_standard_image(self):
        params = self.standard_image_parameters.copy()
        format = params.pop('format',None)  # not used yet
        jpg, params = self.get_latest_jpeg(**params)
        params['format'] = format
        return jpg, params

    def request_specific_images(self, timestamp, num_images=1, offset=(0, 0), size=(3232, 4864), scale_by=1 / 8.,
                                quality=75,
                                format='jepg', step=-1):
        last_index = self.merged_index.get_index_of_timestamp(timestamp)
        first_index = last_index + step * num_images
        logger.debug("request timestamp %f, num_images %d, step %d -> first index: %d, last index: %d, total rows: %d"
                     % (timestamp, num_images, step, first_index, last_index, self.merged_index.df.shape[0]))
        if first_index > last_index:
            first_index, last_index = last_index, first_index
        selection = self.merged_index.df.iloc[first_index, last_index, abs(step)]
        logger.debug("selected %d rows" % selection.shape[0])
        for _,row in selection.iterrows():
            self.sequence_data.append(self.get_image_by_info(row, offset=offset, size=size, scale_by=scale_by,
                                                             quality=quality, format=format))


    def request_specific_file(self, filename, max_num_bytes, file_id, from_end=False):
        timestamp = time.time()
        with open(filename, 'r') as fh:
            if from_end:
                fh.seek(-max_num_bytes, os.SEEK_END)
            data = fh.read(max_num_bytes)
        self.sequence_data.append((data, dict(filename=filename, timestamp=timestamp, file_id=file_id,
                                              file_type=file_format_classes.GeneralFile.file_type)))

    def get_next_data_for_downlink(self):
        if self.sequence_data:
            result = self.sequence_data[0]
            self.sequence_data = self.sequence_data[1:]
        else:
            result = self.get_latest_standard_image()
        return result


class MergedIndex(object):
    def __init__(self, subdirectory_name, data_dirs=DEFAULT_DATA_DIRS):
        self.index_filenames = [os.path.join(data_dir, subdirectory_name, INDEX_FILENAME) for data_dir in data_dirs]
        self.index_filenames = [fn for fn in self.index_filenames if os.path.exists(fn)]
        self.watchers = [IndexWatcher(fn) for fn in self.index_filenames]
        self.df = None
        self.update()

    def update(self):
        new_rows = False
        for watcher in self.watchers:
            fragment = watcher.get_fragment()
            if fragment is not None and fragment.shape[0] > 0:
                new_rows = True
                if self.df is None:
                    self.df = fragment
                else:
                    self.df = pd.concat((self.df, fragment), ignore_index=True)
        if new_rows:
            self.df.sort_values('frame_timestamp_ns', inplace=True)

    def get_latest(self, update=True):
        if update:
            self.update()
        if self.df is not None and self.df.shape[0]:
            return self.df.iloc[-1]
        else:
            return None

    def get_index_of_timestamp(self, timestamp, update=True):
        if update:
            self.update()
        if self.df is None:
            return None
        else:
            return self.df.frame_timestamp_ns.searchsorted(timestamp * 1e9, side='right')[0]


class IndexWatcher(object):
    def __init__(self, filename):
        self.filename = filename
        self.last_position = 0
        self.df = None

    def get_latest(self, update=True):
        if update:
            self.update()
        if self.df is not None and self.df.shape[0]:
            return self.df.iloc[-1]
        else:
            return None

    def get_fragment(self):
        if self.df is not None:
            names = list(self.df.columns)
            header = None
        else:
            names = None
            header = 0
        fragment = None
        with open(self.filename) as fh:
            fh.seek(self.last_position)
            try:
                fragment = pd.read_csv(fh, names=names, header=header)
                if self.df is None:
                    self.df = fragment
            except ValueError:
                pass
            self.last_position = fh.tell()
        return fragment

    def update(self):
        fragment = self.get_fragment()
        if self.df is None:
            self.df = fragment
        else:
            if fragment is not None and fragment.shape[0] > 0:
                self.df = pd.concat((self.df, fragment), ignore_index=True)


if __name__ == "__main__":
    from pmc_camera.utils import log
    log.setup_stream_handler(level=logging.DEBUG)
    ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:50000' % ip)
    except Exception as e:
        print "failed to connect to pipeline:",e
        pipeline = None
    server = SimpleImageServer(pipeline)
    ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
    daemon = Pyro4.Daemon(host=ip, port=50001)
    uri = daemon.register(server, "image")
    print uri
    daemon.requestLoop()

import glob
import os
import time

import PIL
import Pyro4
import logging
import pandas as pd

from pmc_camera.image_processing.jpeg import simple_jpeg
from pmc_camera.image_processing.blosc_file import load_blosc_image

logger = logging.getLogger(__name__)

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle', ]

DEFAULT_DATA_DIRS = ['/data1','/data2','/data3','/data4']
INDEX_FILENAME = 'index.csv'

@Pyro4.expose
class SimpleImageServer(object):
    def __init__(self,data_dirs=DEFAULT_DATA_DIRS):
        self.data_dirs = data_dirs
        self.latest_image_subdir = ''
        self.index_watchers = []
        self.update_current_image_dirs()

    def update_current_image_dirs(self):
        all_dirs = []
        for data_dir in self.data_dirs:
            image_dirs = [os.path.split(x)[1] for x in glob.glob(os.path.join(data_dir,'20*'))]
            all_dirs.extend(image_dirs)
        all_dirs = list(set(all_dirs)) # get just the unique names
        all_dirs.sort()
        latest = all_dirs[-1]
        if latest != self.latest_image_subdir:
            self.latest_image_subdir = latest
            self.current_image_dirs = []
            for data_dir in self.data_dirs:
                candidate = os.path.join(data_dir,latest)
                if os.path.exists(os.path.join(candidate,INDEX_FILENAME)):
                    self.current_image_dirs.append(candidate)
            logger.debug("Found new image subdirectories:\n\t%s" % ('\n\t'.join(self.current_image_dirs)))
            self.index_watchers = [IndexWatcher(os.path.join(d,INDEX_FILENAME)) for d in self.current_image_dirs]

    def get_latest_fileinfo(self):
        candidates = [iw.get_latest() for iw in self.index_watchers]
        candidates = [cand for cand in candidates if cand is not None]
        candidates = pd.DataFrame(candidates)
        candidates.sort_values(['frame_id'],inplace=True)
        if candidates.shape[0]:
            return candidates.iloc[-1]
        else:
            raise RuntimeError("No candidates for latest file!")

    def get_latest_jpeg(self,scale_by=1/8.,resample=PIL.Image.LANCZOS,**kwargs):
        info = self.get_latest_fileinfo()
        image,chunk = load_blosc_image(info.filename)
        return simple_jpeg(image,scale_by=scale_by,resample=resample,**kwargs),info

class IndexWatcher(object):
    def __init__(self, filename):
        self.filename = filename
        self.last_position = 0
        self.df = None
        self.update()

    def get_latest(self,update=True):
        if update:
            self.update()
        if self.df is not None and self.df.shape[0]:
            return self.df.iloc[-1]
        else:
            return None
    def update(self):
        with open(self.filename) as fh:
            if self.df is None:
                try:
                    self.df = pd.read_csv(fh)
                    self.last_position = fh.tell()
                except Exception as e:
                    logger.exception("Failed to parse index file")
                    self.df = None
            else:
                fh.seek(self.last_position)
                fragment = pd.read_csv(fh,names = list(self.df.columns), header=None)
                self.last_position = fh.tell()
                if fragment.shape[0] > 0:
                    self.df = pd.concat((self.df,fragment),ignore_index=True)


if __name__ == "__main__":
    server = SimpleImageServer()
    ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
    daemon = Pyro4.Daemon(host=ip,port=50001)
    uri = daemon.register(server,"image")
    print uri
    daemon.requestLoop()

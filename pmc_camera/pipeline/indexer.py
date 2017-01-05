import os

import pandas as pd

from pmc_camera.pipeline.simple_image_server import DEFAULT_DATA_DIRS, INDEX_FILENAME


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
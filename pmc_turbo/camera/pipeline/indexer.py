import os
import glob
import pandas as pd
import logging

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIRS = ['/data1', '/data2', '/data3', '/data4']
INDEX_FILENAME = 'index.csv'


class MergedIndex(object):
    def __init__(self, subdirectory_name, data_dirs=DEFAULT_DATA_DIRS):
        self.index_filenames = []
        for data_dir in data_dirs:
            self.index_filenames.extend(glob.glob(os.path.join(data_dir, subdirectory_name, INDEX_FILENAME)))
        self.watchers = [IndexWatcher(fn) for fn in self.index_filenames]
        self.df = None
        self.update()

    def update(self):
        new_rows = False
        segment = None
        for watcher in self.watchers:
            fragment = watcher.get_fragment()
            if fragment is not None and fragment.shape[0] > 0:
                logger.debug("Found %d new rows" % fragment.shape[0])
                new_rows = True
                if segment is None:
                    segment = fragment
                else:
                    segment = pd.concat((segment, fragment), ignore_index=True)
        if new_rows:
            segment.sort_values('frame_timestamp_ns', inplace=True)
            if self.df is None:
                self.df = segment
            else:
                self.df = pd.concat((self.df,segment),ignore_index=True)
            logger.debug("index updated with new rows, %d total rows" % self.df.shape[0])
        else:
            if self.df is None:
                msg = "index is empty"
            else:
                msg = "%d total rows" % self.df.shape[0]
            logger.debug("index updated, no new rows, "+ msg)

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
        self.last_modified = 0
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
        modified = os.stat(self.filename).st_mtime
        if modified != self.last_modified:
            with open(self.filename) as fh:
                fh.seek(self.last_position)
                try:
                    fragment = pd.read_csv(fh, names=names, header=header)
                    if self.df is None:
                        self.df = fragment
                except ValueError:
                    pass
                self.last_position = fh.tell()
            self.last_modified = modified
        return fragment

    def update(self):
        fragment = self.get_fragment()
        if self.df is None:
            self.df = fragment
        else:
            if fragment is not None and fragment.shape[0] > 0:
                self.df = pd.concat((self.df, fragment), ignore_index=True)


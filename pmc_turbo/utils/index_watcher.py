import os
import logging

import pandas as pd

logger = logging.getLogger(__name__)


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
                    original_num_rows = fragment.shape[0]
                    fragment.dropna(axis=0,how='any',inplace=True)
                    num_rows_dropped = original_num_rows-fragment.shape[0]
                    if num_rows_dropped:
                        logger.warning("dropped %d rows that had NaNs from file %s" % (num_rows_dropped,self.filename))
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
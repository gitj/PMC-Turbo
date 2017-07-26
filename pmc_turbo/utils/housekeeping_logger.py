import os
import logging
import errno
import time
logger = logging.getLogger(__name__)

class HousekeepingLogger(object):
    def __init__(self, columns,housekeeping_dir):
        self.housekeeping_dir = housekeeping_dir
        self.columns = columns
    def create_log_file(self, header=None):
        try:
            os.makedirs(self.housekeeping_dir)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.housekeeping_dir):
                pass
            else:
                logger.exception("Could not create housekeeping directory %s" % self.housekeeping_dir)

        self.status_log_filename = os.path.join(self.housekeeping_dir, (time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.status_log_file = open(self.status_log_filename, 'a')
        if header is not None:
            if header[-1] != '\n':
                header = header + '\n'
            self.status_log_file.write(header)
        self.status_log_file.write(','.join(self.columns) + '\n')
    def write_log_entry(self,data):
        values = []
        for column in self.columns:
            values.append(data[column])
        self.status_log_file.write(','.join(['%s' % value for value in values]) + '\n')
        self.status_log_file.flush()


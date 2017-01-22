import os
import logging
from pmc_camera.utils import file_reading
import json
import glob
import time

logger = logging.getLogger(__name__)

# These can go into constants file in the future.
from pip._vendor.pyparsing import col

SILENCE = 0
NOMINAL = 1
GOOD = 2
WARNING = 3
CRITICAL = 4
DELIMITER = ','


class StatusGroup(dict):
    def __init__(self, name, groups):
        self.name = name
        for group in groups:
            self[group.name] = group

    def get_status_summary(self):
        values = [self[key].get_status_summary()[0][1] for key in self.keys()]
        max_value = max(values)
        max_indices = [i for i, value in enumerate(values) if value == max_value]
        return [(self.keys()[i], self[self.keys()[i]].get_status_summary()) for i in max_indices]

    def update(self):
        for key in self.keys():
            self[key].update()

    def convert_to_string(self):
        buffer = ''
        for file_key in self.keys():
            for item_key in self[file_key].keys():
                buffer += 'File: %s, item: %s, value: %0.2f, epoch: %0.0f' % (self[file_key].name,
                                                                              self[file_key][item_key].name,
                                                                              self[file_key][item_key].value,
                                                                              self[file_key][item_key].epoch)
                buffer += '\n'
        return buffer

    def to_json(self):
        return json.dumps(self.convert_to_string())


class StatusFileWatcher(dict):
    def __init__(self, name, items, filename_glob):
        # example, charge_controller.csv, charge_controller

        self.glob = filename_glob + '*'

        self.assign_file(self.glob)

        self.last_update = None
        self.name = name

        self.names = None
        for item in items:
            self[item.column_name] = item

    def assign_file(self, filename_glob):
        files = glob.glob(filename_glob)
        if len(files) == 0:
            raise ValueError('No files found with filename_glob %r' % filename_glob)
        files.sort()
        self.source_file = files[-1]
        logger.debug('File %r set' % self.source_file)

    def get_status_summary(self):
        values = [self[key].get_status_summary() for key in self.keys()]
        max_value = max(values)
        max_indices = [i for i, value in enumerate(values) if (value == max_value)]
        return [(self.keys()[i], values[i]) for i in max_indices]

    def update(self):
        if self.names is None:
            with open(self.source_file, 'r') as f:
                f.seek(0, 0)
                self.names = (f.readline().strip('\n')).split(DELIMITER)
                if self.names[0] != 'epoch':
                    raise ValueError('First column of file %r is not epoch' % self.source_file)
        last_update = os.path.getctime(self.source_file)
        if last_update == self.last_update:  # if the file not has changed since last check

            logger.debug('File up to date.')
            return

        else:

            if self.last_update and not (
                        time.localtime(last_update).tm_mday == time.localtime(self.last_update).tm_mday):
                # Flips over to new file for a new day.
                logger.debug('New day, new file')
                self.assign_file(self.glob)

            last_line = file_reading.read_last_line(self.source_file)
            values = last_line.split(DELIMITER)
            self.last_update = last_update

        value_dict = dict(zip(self.names, values))

        logger.debug('Value dict: %r' % value_dict)

        for key in value_dict.keys():

            if key in self:
                logger.debug('updating filewatcher %r, attribute %r with value %r' % (self.name, key, value_dict[key]))
                self[key].update_value(value_dict[key], value_dict['epoch'])


class FloatStatusItem():
    def __init__(self, name, column_name, nominal_range, good_range, warning_range):
        # Example solar cell voltage
        self.name = name
        self.column_name = column_name
        self.value = None
        self.epoch = None
        self.nominal_range = nominal_range
        self.good_range = good_range
        self.warning_range = warning_range
        self.silenced = False

    # Add silence, epoch

    def update_value(self, value, epoch):
        self.value = float(value)
        self.epoch = float(epoch)

    def get_status_summary(self):
        if self.silenced:
            return SILENCE
        if self.nominal_range:
            if self.value in self.nominal_range:
                return NOMINAL
        if self.good_range:
            if self.value in self.good_range:
                return GOOD
        if self.warning_range:
            if self.value in self.warning_range:
                return WARNING
        return CRITICAL


class Range():
    def __init__(self, min, max):
        self.ranges = [(min, max)]

    def __contains__(self, item):
        for range_ in self.ranges:
            if range_[0] <= item <= range_[1]:
                return True
        return False

    def __add__(self, other):
        self.ranges += other.ranges

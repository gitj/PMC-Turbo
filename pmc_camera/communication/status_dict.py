import os
from pmc_camera.utils import file_reading

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


class StatusFileWatcher(dict):
    def __init__(self, name, items, filename):
        # example, charge_controller.csv, charge_controller
        if not os.path.exists(filename):
            raise ValueError('File %r does not exist' % filename)
        self.source_file = filename
        self.last_update = None
        self.name = name

        self.names = None
        for item in items:
            self[item.name] = item

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
        if not last_update == self.last_update:  # if the file has changed since last check
            last_line = file_reading.read_last_line(self.source_file)
            values = last_line.split(DELIMITER)

        value_dict = dict(zip(self.names, values))

        for key in value_dict.keys():
            if key in self:
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

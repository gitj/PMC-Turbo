import glob
import json
import logging
import os
import time

from pmc_turbo.pmc_camera.communication import file_format_classes

from pmc_turbo.pmc_camera.utils import file_reading

logger = logging.getLogger(__name__)

# These can go into constants file in the future.

SILENCE = 0
NOMINAL = 1
GOOD = 2
WARNING = 3
CRITICAL = 4
DELIMITER = ','


def construct_super_group_from_csv_list(group_name, csv_paths_and_preambles):
    """

    Parameters
    ----------
    group_name - string
    csv_paths_and_preambles - tuple - string csv_path, string csv_preamble_to_glob

    Returns
    -------
    SuperStatusGroup

    """
    super_group = SuperStatusGroup(group_name, groups=[])
    for csv_path_and_preamble in csv_paths_and_preambles:
        csv_path, csv_preamble = csv_path_and_preamble
        status_group = construct_status_group_from_csv(csv_path, csv_path, csv_preamble)
        super_group.groups.append(status_group)
    return super_group


def construct_status_group_from_csv(group_name, csv_path, csv_preamble):
    status_group = StatusGroup(group_name, filewatchers=[])
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    column_names = lines[0].strip('\n').split(',')
    for line in lines[1:]:
        values = line.strip('\n').split(',')
        value_dict = dict(zip(column_names, values))

        filewatcher_name = value_dict['partial_glob']
        all_filewatcher_names = [filewatcher.name for filewatcher in status_group.filewatchers]

        if not filewatcher_name in all_filewatcher_names:
            status_filewatcher = StatusFileWatcher(name=value_dict['partial_glob'], items=[],
                                                   filename_glob=os.path.join(csv_preamble, value_dict['partial_glob']))
            status_group.filewatchers.append(status_filewatcher)
        status_item = FloatStatusItem(name=values[1], column_name=value_dict['column_name'],
                                      scaling=value_dict['scaling_value'],
                                      good_range=Range(value_dict['good_range_low'], value_dict['good_range_high']),
                                      nominal_range=Range(value_dict['normal_range_low'],
                                                          value_dict['normal_range_high']),
                                      warning_range=Range(value_dict['warning_range_low'],
                                                          value_dict['warning_range_high']))
        for filewatcher in status_group.filewatchers:
            if filewatcher.name == filewatcher_name:
                filewatcher.items.append(status_item)

    return status_group


class SuperStatusGroup():
    def __init__(self, name, groups):
        self.name = name
        self.groups = groups

    def get_status_summary(self):
        status_summaries = [group.get_status_summary() for group in self.groups]
        max_value = max([status_summary[0] for status_summary in status_summaries])
        name_list = []
        for status_summary in status_summaries:
            if status_summary[0] == max_value:
                name_list += status_summary[1]
        return (max_value, name_list)

    def update(self):
        logger.debug('Updating %r' % self.name)
        for group in self.groups:
            group.update()

    def to_json_file(self):
        payload = json.dumps(self.get_status())
        json_file = file_format_classes.GeneralFile(payload=payload, filename='json_file.json', timestamp=time.time(),
                                                    camera_id=0, request_id=000)
        return json_file

    def get_status(self):
        if len(self.groups) == 0:
            raise ValueError('No groups - filewatcher is empty.')
        entries = {group.name: group.get_status() for group in self.groups}
        return entries


class StatusGroup():
    def __init__(self, name, filewatchers):
        self.name = name
        self.filewatchers = filewatchers

    def get_status_summary(self):
        status_summaries = [filewatcher.get_status_summary() for filewatcher in self.filewatchers]
        max_value = max([status_summary[0] for status_summary in status_summaries])
        name_list = []
        for status_summary in status_summaries:
            if status_summary[0] == max_value:
                name_list += status_summary[1]
        return (max_value, name_list)

    def update(self):
        logger.debug('Updating %r' % self.name)
        for filewatcher in self.filewatchers:
            filewatcher.update()

    def to_json_file(self):
        payload = json.dumps(self.get_status())
        json_file = file_format_classes.GeneralFile(payload=payload, filename='json_file.json', timestamp=time.time(),
                                                    camera_id=0, request_id=000)
        return json_file

    def get_status(self):
        if len(self.filewatchers) == 0:
            raise ValueError('No filewatchers - filewatcher is empty.')
        entries = {filewatcher.name: filewatcher.get_status() for filewatcher in self.filewatchers}
        return entries


class MultiStatusFileWatcher(dict):
    def __init__(self, name, filewatchers):
        self.name = name
        self.filewatchers = filewatchers

    def update(self):
        for filewatcher in self.filewatchers:
            filewatcher.update()

    def get_status(self):
        statuses = [filewatcher.get_status() for filewatcher in self.filewatchers]
        mydict = {}
        for status in statuses:
            mydict.update(status)
        return mydict

    def get_status_summary(self):
        status_summaries = [filewatchers.get_status_summary() for filewatchers in self.filewatchers]
        max_value = max([status_summary[0] for status_summary in status_summaries])
        name_list = []
        for status_summary in status_summaries:
            if status_summary[0] == max_value:
                name_list += status_summary[1]
        return (max_value, name_list)


class StatusFileWatcher():
    def __init__(self, name, items, filename_glob):
        # example, charge_controller.csv, charge_controller

        self.glob = filename_glob

        self.assign_file(self.glob)

        self.last_update = None
        self.name = name

        self.column_names = None
        self.items = items

    def assign_file(self, filename_glob):
        files = glob.glob(filename_glob)
        if len(files) == 0:
            raise ValueError('No files found with filename_glob %r' % filename_glob)
        files.sort()
        self.source_file = files[-1]
        logger.debug('File %r set' % self.source_file)

    def get_status_summary(self):
        if len(self.items) == 0:
            raise ValueError('No items - filewatcher is empty.')
        values = [item.get_status_summary() for item in self.items]
        max_value = max(values)
        max_indices = [i for i, value in enumerate(values) if (value == max_value)]
        return (max_value, [self.items[i].name for i in max_indices])

    def get_status(self):
        if len(self.items) == 0:
            raise ValueError('No items - filewatcher is empty.')
        entries = (item.get_status() for item in self.items)
        return dict(zip(self.items, entries))

    def update(self):
        logger.debug('Updating %r' % self.name)
        if self.column_names is None:
            logger.debug('Getting column names')
            with open(self.source_file, 'r') as f:
                f.seek(0, 0)
                name_line = f.readline()
                if name_line.startswith('#'):
                    # Ignore headers
                    name_line = f.readline()
                self.column_names = (name_line.strip('\n')).split(DELIMITER)
                if self.column_names[0] != 'epoch':
                    raise ValueError(
                        'First column of file %r is not epoch, it is %r' % (self.source_file, self.column_names[0]))
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

        if len(values) != len(self.column_names):
            raise ValueError('Number of values and column names mismatch. %d Values, %d column names' %
                             (len(values), len(self.column_names)))
        value_dict = dict(zip(self.column_names, values))

        for item in self.items:
            item.update_value(value_dict)


class FloatStatusItem():
    def __init__(self, name, column_name, nominal_range, good_range, warning_range, scaling=1):
        # Example solar cell voltage
        self.name = name
        self.column_name = column_name
        self.value = None
        self.epoch = None
        self.nominal_range = nominal_range
        self.good_range = good_range
        self.warning_range = warning_range
        self.silenced = False
        self.scaling = float(scaling)

    # Add silence, epoch

    def update_value(self, value_dict):
        if self.column_name in value_dict:
            self.value = float(value_dict[self.column_name])
            self.value *= self.scaling
        self.epoch = float(value_dict['epoch'])
        logger.debug('Item %r updated with value %r' % (self.name, self.value))

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

    def get_status(self):
        return dict(column_name=self.column_name, value=self.value, epoch=self.epoch)


class StringStatusItem():
    def __init__(self, name, column_name, nominal_string, good_string, warning_string):
        # Example solar cell voltage
        self.name = name
        self.column_name = column_name
        self.value = None
        self.epoch = None
        self.nominal_string = nominal_string
        self.good_string = good_string
        self.warning_string = warning_string
        self.silenced = False

    # Add silence, epoch

    def update_value(self, value_dict):
        if self.column_name in value_dict:
            self.value = str(value_dict[self.column_name])
            self.epoch = float(value_dict['epoch'])
            logger.debug('Item %r updated with value %r' % (self.name, self.value))

    def get_status_summary(self):
        if self.silenced:
            return SILENCE
        if self.nominal_string:
            if self.nominal_string in self.value:
                return NOMINAL
        if self.good_string:
            if self.good_string in self.value:
                return GOOD
        if self.warning_string:
            if self.warning_string in self.value:
                return WARNING
        return CRITICAL

    def get_status(self):
        return dict(column_name=self.column_name, value=self.value, epoch=self.epoch)


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

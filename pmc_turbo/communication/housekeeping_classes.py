import glob
import json
import logging
import os
import time
import math

from pmc_turbo.communication import file_format_classes
from pmc_turbo.utils import file_reading

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
        super_group.groups[status_group.name] = status_group
    return super_group


def construct_status_group_from_csv(group_name, csv_path, csv_preamble):
    status_group = StatusGroup(group_name, filewatchers=[])
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    column_names = lines[0].strip('\n').split(',')
    for line in lines[1:]:
        values = line.strip('\n').split(',')
        value_dict = dict(zip(column_names, values))
        if not value_dict['partial_glob'] in status_group.filewatchers.keys():
            status_filewatcher = StatusFileWatcher(name=value_dict['partial_glob'], items=[],
                                                   filename_glob=os.path.join(csv_preamble, value_dict['partial_glob']))
            status_group.filewatchers[value_dict['partial_glob']] = status_filewatcher
        try:
            status_item = eval(value_dict['class_type'])(value_dict)
        except Exception as e:
            logger.debug('Problem while trying to create status_item. Value dict is: %r' % value_dict)
            raise e

        status_group.filewatchers[value_dict['partial_glob']].items[status_item.name] = status_item

    return status_group


def construct_status_group_from_json(group_name, json_path, json_range_path):
    status_group = StatusGroup(group_name, filewatchers=[])

    with open(json_path, 'r') as f:
        result = json.loads(f.read())
    with open(json_range_path, 'r') as f:
        range_result = json.loads(f.read())

    for key in range_result.keys():
        try:
            result[key].update(range_result[key])
        except KeyError as e:
            logger.debug(' Could not find key %r in results from json.' % key)
            raise e

    for value_key in result.keys():
        value_dict = result[value_key]
        if not value_dict['partial_glob'] in status_group.filewatchers.keys():
            status_filewatcher = StatusFileWatcher(name=value_dict['partial_glob'], items=[],
                                                   filename_glob=os.path.join(value_dict['partial_glob']))
            status_group.filewatchers[value_dict['partial_glob']] = status_filewatcher
        try:
            status_item = eval(value_dict['class_type'])(value_dict)
        except Exception as e:
            logger.debug('Problem while trying to create status_item. Value dict is: %r' % value_dict)
            raise e

        status_group.filewatchers[value_dict['partial_glob']].items.update({status_item.name: status_item})

        status_group.filewatchers[value_dict['partial_glob']].items[status_item.name] = status_item

    return status_group


def construct_super_group_from_json_list(group_name, json_paths, json_range_paths):
    super_group = SuperStatusGroup(group_name, groups=[])
    for json_path, json_range_path in zip(json_paths, json_range_paths):
        status_group = construct_status_group_from_json(json_path, json_range_path)
        super_group.groups[status_group.name] = status_group
    return super_group


class SuperStatusGroup():
    def __init__(self, name, groups):
        self.name = name
        self.groups = {}
        for group in groups:
            self.groups[group.name] = group

    def get_status_summary(self):
        status_summaries = [self.groups[key].get_status_summary() for key in self.groups.keys()]
        max_value = max([status_summary[0] for status_summary in status_summaries])
        name_list = []
        for status_summary in status_summaries:
            if status_summary[0] == max_value:
                name_list += status_summary[1]
        return (max_value, name_list)

    def update(self):
        logger.debug('Updating %r' % self.name)
        for key in self.groups.keys():
            self.groups[key].update()

    def to_json_file(self):
        payload = json.dumps(self.get_status())
        json_file = file_format_classes.GeneralFile(payload=payload, filename='json_file.json', timestamp=time.time(),
                                                    camera_id=0, request_id=000)
        return json_file

    def get_status(self):
        if len(self.groups.keys()) == 0:
            raise ValueError('No keys - filewatcher is empty.')
        entries = {key: self.groups[key].get_status() for key in self.groups.keys()}
        return entries

    def get_255_byte_summary(self):
        """

        Returns
        1-byte status for each status_item that has an important flag (put in correct place in 255-length array
        -------

        """

        # TODO: Make important flag - fill out 255 bytes

        return


class StatusGroup():
    def __init__(self, name, filewatchers):
        self.name = name
        self.filewatchers = {}
        for filewatcher in filewatchers:
            self.filewatchers[filewatcher.name] = filewatcher

    def get_status_summary(self):
        status_summaries = [self.filewatchers[key].get_status_summary() for key in self.filewatchers.keys()]
        max_value = max([status_summary[0] for status_summary in status_summaries])
        name_list = []
        for status_summary in status_summaries:
            if status_summary[0] == max_value:
                name_list += status_summary[1]
        return (max_value, name_list)

    def update(self):
        logger.debug('Updating %r' % self.name)
        for key in self.filewatchers.keys():
            self.filewatchers[key].update()

    def convert_to_string(self):
        buffer = ''
        for file_key in self.filewatchers.keys():
            for item_key in self.filewatchers[file_key].keys():
                buffer += 'File: %s, item: %s, value: %0.2f, epoch: %0.0f' % (self[file_key].name,
                                                                              self[file_key][item_key].name,
                                                                              self[file_key][item_key].value,
                                                                              self[file_key][item_key].epoch)
                buffer += '\n'
        return buffer

    def to_json_file(self):
        payload = json.dumps(self.get_status())
        json_file = file_format_classes.GeneralFile(payload=payload, filename='json_file.json', timestamp=time.time(),
                                                    camera_id=0, request_id=000)
        return json_file

    def get_status(self):
        if len(self.filewatchers.keys()) == 0:
            raise ValueError('No keys - filewatcher is empty.')
        entries = {key: self.filewatchers[key].get_status() for key in self.filewatchers.keys()}
        return entries


class MultiStatusFileWatcher():
    def __init__(self, name, filewatchers):
        self.name = name
        self.filewatchers = {}
        for filewatcher in filewatchers:
            self.filewatchers[filewatcher.name] = filewatcher

    def update(self):
        for key in self.filewatchers.keys():
            self.filewatchers[key].update()

    def get_status(self):
        statuses = [self.filewatchers[key].get_status() for key in self.filewatchers.keys()]
        mydict = {}
        for status in statuses:
            mydict.update(status)
        return mydict

    def get_status_summary(self):
        status_summaries = [self.filewatchers[key].get_status_summary() for key in self.filewatchers.keys()]
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
        self.items = {}
        for item in items:
            self.items[item.name] = item

    def assign_file(self, filename_glob):
        files = glob.glob(filename_glob)
        if len(files) == 0:
            raise ValueError('No files found with filename_glob %r' % filename_glob)
        files.sort()
        self.source_file = files[-1]
        logger.debug('File %r set' % self.source_file)

    def get_status_summary(self):
        if len(self.items.keys()) == 0:
            raise ValueError('No keys - filewatcher is empty.')
        values = [self.items[key].get_status_summary() for key in self.items.keys()]
        max_value = max(values)
        max_indices = [i for i, value in enumerate(values) if (value == max_value)]
        return (max_value, [self.items.keys()[i] for i in max_indices])

    def get_status(self):
        if len(self.items.keys()) == 0:
            raise ValueError('No keys - filewatcher is empty.')
        entries = (self.items[key].get_status() for key in self.items.keys())
        return dict(zip(self.items.keys(), entries))

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

        for key in self.items.keys():
            self.items[key].update_value(value_dict)


class FloatStatusItem():
    def __init__(self, value_dict):
        # Example solar cell voltage
        self.name = value_dict['column_name']
        self.column_name = value_dict['column_name']
        self.value = None
        self.epoch = None
        self.normal_range = Range(float(value_dict['normal_range_low']), float(value_dict['normal_range_high']))
        self.good_range = Range(float(value_dict['good_range_low']), float(value_dict['good_range_high']))
        self.warning_range = Range(float(value_dict['warning_range_low']), float(value_dict['warning_range_high']))
        self.silenced = False
        self.scaling = float(value_dict['scaling_value'])

    # Add silence, epoch

    def update_value(self, value_dict):
        if self.column_name in value_dict:
            self.unscaled_value = float(value_dict[self.column_name])
            self.value = self.unscaled_value * self.scaling
        self.epoch = float(value_dict['epoch'])
        logger.debug('Item %r updated with value %r' % (self.name, self.value))

    def get_status_summary(self):
        if self.silenced:
            return SILENCE
        if self.normal_range:
            if self.value in self.normal_range:
                return NOMINAL
        if self.good_range:
            if self.value in self.good_range:
                return GOOD
        if self.warning_range:
            if self.value in self.warning_range:
                return WARNING
        return CRITICAL

    def get_status(self):
        # TODO: Add unscaled value and scaling if scaling != 1
        return dict(column_name=self.column_name, value=self.value, epoch=self.epoch)


class StringStatusItem():
    def __init__(self, value_dict):
        # Example solar cell voltage
        self.name = value_dict['column_name']
        self.column_name = value_dict['column_name']
        self.value = None
        self.epoch = None
        self.normal_string = value_dict['normal_string']
        self.good_string = value_dict['good_string']
        self.warning_string = value_dict['warning_string']
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
        if self.normal_string:
            if self.normal_string in self.value:
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

        if not (isinstance(min, int) or isinstance(min, float)):
            raise TypeError("Min %r is not an int or float. It is a %r" % (min, type(min)))

        if not (isinstance(max, int) or isinstance(max, float)):
            raise TypeError("Max %r is not an int or float. It is a %r " % (max, type(max)))

        if min == float('nan') and max != float('nan'):
            raise ValueError('Either both min or max are float or neither are. Only min is float.')

        if max == float('nan') and min != float('nan'):
            raise ValueError('Either both min or max are float or neither are. Only max is float.')

        self.ranges = [(min, max)]

    def __contains__(self, item):
        for range_ in self.ranges:
            if math.isnan(range_[0]) or math.isnan(range_[1]):
                return True

            if range_[0] <= item <= range_[1]:
                return True

            else:
                return False

        return False

    def __add__(self, other):
        self.ranges += other.ranges

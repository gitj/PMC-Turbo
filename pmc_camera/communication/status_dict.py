import os
import glob

# These can go into constants file in the future.
NOMINAL = 1
GOOD = 2
WARNING = 3
CRITICAL = 4
DELIMITER = ','


class StatusGroup(dict):
    def __init__(self, name, groups):
        self.name = name
        self.groups = groups

    def get_status_summary(self):
        values = [group.get_status_summary[0][1] for group in self.groups]
        max_value = max(values)
        max_indices = [i for i, value in values if value == max_value]

        return [((group.name, [item_name for item_name, item_status_summary in group.get_status_summary]), max_value)
                for group in self.groups[max_indices]]

    def update(self):
        for group in self.groups:
            group.update()


class StatusFileWatcher(dict):
    def __init__(self, name, items, filename):
        # example, charge_controller.csv, charge_controller
        if not os.path.exists(filename):
            raise ValueError('File %r does not exist' % filename)
        self.source_file = filename
        self.last_update = None
        self.name = name
        self.items = items

    def get_status_summary(self):
        # This code works, but I can clean it up
        values = [item.get_status_summary for item in self.items]
        max_value = max(values)
        max_indices = [i for i, value in values if value == max_value]
        return [(item.name, item.get_status_summary) for item in self.items[max_indices]]

    def update(self):
        last_update = os.path.getctime(self.source_file)
        if not last_update == self.last_update:  # if the file has changed since last check
            with open(self.source_file, 'r') as f:
                lines = f.readlines()
                names = lines[0].split(DELIMITER)
                values = lines[-1].split(DELIMITER)
        for i, item_name in enumerate(names):
            self["item_name"].value = values[i]


class StatusItem():
    def __init__(self, name, value, nominal_range, good_range, warning_range):
        # Example solar cell voltage
        self.name = name
        self.value = value
        self.nominal_range = nominal_range
        self.good_range = good_range
        self.warning_range = warning_range

    def update_value(self, value):
        self.value = value

    def get_status_summary(self):
        if self.value in self.nominal_range:
            return NOMINAL
        if self.value in self.good_range:
            return GOOD
        if self.value in self.warning_range:
            return WARNING
        return CRITICAL

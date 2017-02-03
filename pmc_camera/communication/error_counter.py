import time
import csv


class CSVWriter(dict):
    def __init__(self, csv_filename, **kwargs):
        self.filename = csv_filename
        for key, value in kwargs.iteritems():
            self[key] = value

    def create_file(self):
        with open(self.filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['epoch'] + self.keys())

    def write_to_file(self):
        with open(self.filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerow([time.time()] + [self[key] for key in self.keys()])

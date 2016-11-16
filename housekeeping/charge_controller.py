import os
import time
import select
import Pyro4
from pymodbus.client.sync import ModbusTcpClient

LOG_DIR = '/home/pmc/logs/charge_controller'
serial_number = 16050331
device_name = 'TriStar-MPPT-60'
NUM_REGISTERS = 92


class ChargeController():
    def __init__(self):
        self.client = ModbusTcpClient('192.168.1.199', port=502)
        self.serialNumber = serial_number
        self.deviceName = device_name
        self.measurement = None
        self.readable_values = {}

    def measure(self):
        self.measurement = self.client.read_input_registers(0, NUM_REGISTERS, unit=0x01).registers


class ChargeControllerLogger():
    def __init__(self, measurement_interval=10):
        try:
            os.mkdir(LOG_DIR)
        except OSError:
            pass
        self.charge_controller = ChargeController()
        self.filename = None
        self.file = None
        self.last_measurement = None
        self.measurement_interval = measurement_interval
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=42000)
        print self.daemon.register(self, objectId='chargecontroller')

    def create_file(self, log_dir=LOG_DIR):
        self.filename = os.path.join(log_dir, (time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.file = open(self.filename, 'a')
        header = ('# %s Serial No %d\n' % (self.charge_controller.deviceName, self.charge_controller.serialNumber))
        self.file.write(header)
        columns = ['epoch'] + [('%d' % x) for x in range(NUM_REGISTERS)]
        self.file.write(','.join(columns) + '\n')
        self.file.flush()

    def measure(self):
        self.charge_controller.measure()
        epoch = time.time()
        return [epoch] + self.charge_controller.measurement

    def show_priority_values(self):
        return populate_human_readable_dict(self.last_measurement)

    def run(self):
        while True:
            self.last_measurement = self.measure()
            if self.file is None:
                self.create_file()
            self.file.write((','.join([('%f' % x) for x in self.last_measurement]) + '\n'))
            self.file.flush()
            while time.time() - self.last_measurement[0] < self.measurement_interval:
                events, _, _ = select.select(self.daemon.sockets, [], [], 0.1)
                if events:
                    self.daemon.events(events)


def populate_human_readable_dict(measurement_array):
    priority_values = {}
    epoch = measurement_array[0]
    voltage_scaling = measurement_array[1] + (measurement_array[2] / 16.)
    current_scaling = measurement_array[3] + (measurement_array[4] / 16.)
    priority_values['epoch'] = epoch
    priority_values['battery_voltage'] = measurement_array[27] * voltage_scaling
    priority_values['battery_current'] = measurement_array[29] * current_scaling
    priority_values['solar_current'] = measurement_array[30] * current_scaling

    return priority_values

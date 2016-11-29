import os
import time
import select
import Pyro4
try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    pass

LOG_DIR = '/home/pmc/logs/housekeeping/charge_controller'
serial_number = 16050331
device_name = 'TriStar-MPPT-60'
NUM_REGISTERS = 92
FIRST_BATCH_START = 5403
NUM_EEPROM_REGISTERS_FIRST_BATCH = 7
SECOND_BATCH_START = 57344
NUM_EEPROM_REGISTERS_SECOND_BATCH = 34
THIRD_BATCH_START = 57472
NUM_EEPROM_REGISTERS_THIRD_BATCH = 13
NUM_COIL_REGISTERS = 26

@Pyro4.expose
class ChargeController():
    def __init__(self):
        self.client = ModbusTcpClient('192.168.1.199', port=502)
        self.serialNumber = serial_number
        self.deviceName = device_name
        self.measurement = None
        self.eeprom_measurement = None
        self.coil_measurement = None
        self.readable_values = {}

    def measure(self):
        self.measurement = self.client.read_input_registers(0, NUM_REGISTERS, unit=0x01).registers

    def measure_eeprom(self):
        self.eeprom_measurement = self.client.read_input_registers(FIRST_BATCH_START, NUM_EEPROM_REGISTERS_FIRST_BATCH,
                                                                   unit=0x01).registers
        self.eeprom_measurement += self.client.read_input_registers(SECOND_BATCH_START, NUM_EEPROM_REGISTERS_SECOND_BATCH,
                                                                    unit=0x01).registers
        self.eeprom_measurement += self.client.read_input_registers(THIRD_BATCH_START, NUM_EEPROM_REGISTERS_THIRD_BATCH,
                                                                    unit=0x01).registers

    def measure_coils(self):
        self.coil_measurement = self.client.read_coils(0, NUM_COIL_REGISTERS, unit=0x01).bits

@Pyro4.expose
class ChargeControllerLogger():
    def __init__(self, measurement_interval=10, record_eeprom=False, eeprom_measurement_interval=60):
        try:
            os.makedirs(LOG_DIR)
        except OSError:
            pass
        self.charge_controller = ChargeController()
        self.filename = None
        self.file = None
        self.last_measurement = None
        self.last_eeprom_measurement = None
        self.measurement_interval = measurement_interval
        self.record_eeprom = record_eeprom
        if self.record_eeprom:
            self.eeprom_measurement_interval = eeprom_measurement_interval
            self.eeprom_filename = None
            self.eeprom_file = None
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=42000)
        print self.daemon.register(self, objectId='chargecontroller')

    def create_file(self, log_dir=LOG_DIR):
        self.filename = os.path.join(log_dir, (time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.file = open(self.filename, 'a')
        header = ('# %s Serial No %d\n' % (self.charge_controller.deviceName, self.charge_controller.serialNumber))
        self.file.write(header)
        columns = ['epoch'] + [('%d' % x) for x in range(1, NUM_REGISTERS+1)]
        self.file.write(','.join(columns) + '\n')
        self.file.flush()

    def create_eeprom_file(self, log_dir=LOG_DIR):
        self.eeprom_filename = os.path.join(log_dir, (time.strftime('%Y-%m-%d_%H%M%S__eeprom.csv')))
        self.eeprom_file = open(self.eeprom_filename, 'a')
        header = ('# %s Serial No %d\n' % (self.charge_controller.deviceName, self.charge_controller.serialNumber))
        self.eeprom_file.write(header)
        index_list = range(FIRST_BATCH_START+1, FIRST_BATCH_START+NUM_EEPROM_REGISTERS_FIRST_BATCH+1)
        index_list += range(SECOND_BATCH_START+1, SECOND_BATCH_START+NUM_EEPROM_REGISTERS_SECOND_BATCH+1)
        index_list += range(THIRD_BATCH_START+1, THIRD_BATCH_START+NUM_EEPROM_REGISTERS_THIRD_BATCH+1)
        index_list += range(1, NUM_COIL_REGISTERS+1)
        columns = ['epoch'] + [('%d' % x) for x in index_list]
        self.eeprom_file.write(','.join(columns) + '\n')
        self.eeprom_file.flush()

    def measure(self):
        self.charge_controller.measure()
        epoch = time.time()
        return [epoch] + self.charge_controller.measurement

    def measure_eeprom_and_coils(self):
        self.charge_controller.measure_eeprom()
        self.charge_controller.measure_coils()
        epoch = time.time()
        return [epoch] + self.charge_controller.eeprom_measurement + self.charge_controller.coil_measurement

    def show_priority_values(self):
        return populate_human_readable_dict(self.last_measurement)

    def run(self):
        while True:
            self.last_measurement = self.measure()
            if self.file is None:
                self.create_file()
            self.file.write((','.join([('%f' % x) for x in self.last_measurement]) + '\n'))
            self.file.flush()

            if self.record_eeprom:
                if (self.last_eeprom_measurement == None) or (time.time() - self.last_eeprom_measurement[0] > self.eeprom_measurement_interval):
                    if self.eeprom_file is None:
                        self.create_eeprom_file()
                    self.last_eeprom_measurement = self.measure_eeprom_and_coils()
                    self.eeprom_file.write((','.join([('%f' % x) for x in self.last_eeprom_measurement]) + '\n'))
                    self.eeprom_file.flush()

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
    priority_values['battery_voltage'] = measurement_array[25] * voltage_scaling * 2.**-15
    priority_values['solar_voltage'] = measurement_array[28] * voltage_scaling * 2.**-15
    priority_values['battery_current'] = measurement_array[29] * current_scaling * 2.**-15
    priority_values['solar_current'] = measurement_array[30] * current_scaling * 2.**-15
    priority_values['charge_state'] = measurement_array[51]
    priority_values['target_voltage'] = measurement_array[52] * voltage_scaling * 2.**-15
    priority_values['output_power'] = measurement_array[59] * voltage_scaling * current_scaling * 2.**-17
    priority_values['heatsink_t'] = measurement_array[36]
    priority_values['battery_t'] = measurement_array[38]

    return priority_values

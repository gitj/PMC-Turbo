import os
import time
import select
import Pyro4
from collections import OrderedDict

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    print 'Unable to import ModbusTcpClient'
    pass

LOG_DIR = '/home/pmc/logs/housekeeping/charge_controller'
# serial_number = 16050331
device_name = 'TriStar-MPPT-60'
NUM_REGISTERS = 92
# FIRST_BATCH_START = 5403
# NUM_EEPROM_REGISTERS_FIRST_BATCH = 7
# SECOND_BATCH_START = 57344
# NUM_EEPROM_REGISTERS_SECOND_BATCH = 34
# THIRD_BATCH_START = 57472
# NUM_EEPROM_REGISTERS_THIRD_BATCH = 13


EEPROM_BATCH_1 = (0x151B, 0x1521 + 1)
EEPROM_BATCH_2 = (0xE000, 0xE021 + 1)
EEPROM_BATCH_3 = (0xE080, 0xE0CD + 1)
EEPROM_REGISTER_INDICES = range(*EEPROM_BATCH_1) + range(*EEPROM_BATCH_2) + range(*EEPROM_BATCH_3)

NUM_COIL_REGISTERS = 26


@Pyro4.expose
class ChargeController():
    def __init__(self, host='pmc-charge-controller-0', port=502):
        self.client = ModbusTcpClient(host=host, port=port)
        self.update_serial_number_and_device_name()
        self.readable_values = {}
        self.coil_register_indices = range(1, NUM_COIL_REGISTERS + 1)

    def update_serial_number_and_device_name(self):
        self.measure_eeprom()
        serial_number_bytes = [('%04x' % self.eeprom_measurement[k])[::-1] for k in range(57536, 57540)]
        self.serial_number = ''.join(serial_number_bytes)[::2]
        device_model = self.eeprom_measurement[0xE0CC]
        if device_model:
            self.device_name = 'TriStar-MPPT-60'
        else:
            self.device_name = 'TriStar-MPPT-45'

    def measure(self):
        measurement = OrderedDict(epoch=time.time())
        result = self.client.read_input_registers(0, NUM_REGISTERS, unit=0x01)
        try:
            measurement.update(zip(range(NUM_REGISTERS), result.registers))
        except AttributeError as e:
            print e, result
            raise
        self.measurement = measurement
        return self.measurement

    def measure_eeprom(self):
        self.eeprom_measurement = OrderedDict(epoch=time.time())
        eeprom_measurement = self.client.read_input_registers(EEPROM_BATCH_1[0], EEPROM_BATCH_1[1] - EEPROM_BATCH_1[0],
                                                              unit=0x01).registers
        eeprom_measurement += self.client.read_input_registers(EEPROM_BATCH_2[0], EEPROM_BATCH_2[1] - EEPROM_BATCH_2[0],
                                                               unit=0x01).registers
        eeprom_measurement += self.client.read_input_registers(EEPROM_BATCH_3[0], EEPROM_BATCH_3[1] - EEPROM_BATCH_3[0],
                                                               unit=0x01).registers
        self.eeprom_measurement.update(zip(EEPROM_REGISTER_INDICES, eeprom_measurement))
        return self.eeprom_measurement

    def measure_coils(self):
        self.coil_measurement = OrderedDict(epoch=time.time())
        self.coil_measurement.update(
            zip(range(NUM_COIL_REGISTERS), self.client.read_coils(0, NUM_COIL_REGISTERS, unit=0x01).bits))
        return self.coil_measurement


@Pyro4.expose
class ChargeControllerLogger():
    def __init__(self, host='pmc-charge-controller-0', port=502, measurement_interval=10, record_eeprom=True,
                 eeprom_measurement_interval=3600):
        try:
            os.makedirs(LOG_DIR)
        except OSError:
            pass
        self.charge_controller = ChargeController(host, port)
        self.filename = None
        self.host = host
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
        self.filename = os.path.join(log_dir, (self.host + '_' + time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.file = open(self.filename, 'a')
        header = ('# %s Serial No %s\n' % (self.charge_controller.device_name, self.charge_controller.serial_number))
        self.file.write(header)
        columns = ['epoch'] + [('register_%d' % x) for x in range(1, NUM_REGISTERS + 1)]
        self.file.write(','.join(columns) + '\n')
        self.file.flush()

    def create_eeprom_file(self, log_dir=LOG_DIR):
        self.eeprom_filename = os.path.join(log_dir, (self.host + '_' + time.strftime('%Y-%m-%d_%H%M%S__eeprom.csv')))
        self.eeprom_file = open(self.eeprom_filename, 'a')
        header = ('# %s Serial No %s\n' % (self.charge_controller.device_name, self.charge_controller.serial_number))
        self.eeprom_file.write(header)
        columns = ['epoch'] + [('eeprom_%d' % x) for x in EEPROM_REGISTER_INDICES]
        self.eeprom_file.write(','.join(columns) + '\n')
        self.eeprom_file.flush()

    def show_priority_values(self):
        return populate_human_readable_dict(self.last_measurement)

    def run(self):
        while True:
            try:
                self.last_measurement = self.charge_controller.measure()
            except AttributeError:
                pass
            else:
                if self.file is None:
                    self.create_file()
                line_to_write = '%f,' % self.last_measurement.values()[0]
                line_to_write += (','.join([('%d' % x) for x in self.last_measurement.values()[1:]]) + '\n')
                self.file.write(line_to_write)
                self.file.flush()

            if self.record_eeprom:
                if (self.last_eeprom_measurement == None) or (
                                time.time() - self.last_eeprom_measurement['epoch'] > self.eeprom_measurement_interval):
                    if self.eeprom_file is None:
                        self.create_eeprom_file()
                    self.last_eeprom_measurement = self.charge_controller.measure_eeprom()
                    line_to_write = '%f,' % self.last_eeprom_measurement.values()[0]
                    line_to_write += (','.join([('%d' % x) for x in self.last_eeprom_measurement.values()[1:]]) + '\n')
                    self.eeprom_file.write(line_to_write)
                    self.eeprom_file.flush()

            while time.time() - self.last_measurement['epoch'] < self.measurement_interval:
                events, _, _ = select.select(self.daemon.sockets, [], [], 0.1)
                if events:
                    self.daemon.events(events)


def populate_human_readable_dict(measurement_array):
    priority_values = {}
    epoch = measurement_array[0]
    voltage_scaling = measurement_array[1] + (measurement_array[2] / 16.)
    current_scaling = measurement_array[3] + (measurement_array[4] / 16.)
    priority_values['epoch'] = epoch
    priority_values['battery_voltage'] = measurement_array[25] * voltage_scaling * 2. ** -15
    priority_values['solar_voltage'] = measurement_array[28] * voltage_scaling * 2. ** -15
    priority_values['battery_current'] = measurement_array[29] * current_scaling * 2. ** -15
    priority_values['solar_current'] = measurement_array[30] * current_scaling * 2. ** -15
    priority_values['charge_state'] = measurement_array[51]
    priority_values['target_voltage'] = measurement_array[52] * voltage_scaling * 2. ** -15
    priority_values['output_power'] = measurement_array[59] * voltage_scaling * current_scaling * 2. ** -17
    priority_values['heatsink_t'] = measurement_array[36]
    priority_values['battery_t'] = measurement_array[38]

    return priority_values


if __name__ == "__main__":
    ccl = ChargeControllerLogger()
    ccl.run()

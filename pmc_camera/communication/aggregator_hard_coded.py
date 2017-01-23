from pmc_camera.communication import status_dict
import logging
import time


def setup_group():
    path = '/var/lib/collectd/csv/pmc-camera-?.unassigned-domain/ipmi/voltage-12V system_board (7.17)-*'
    voltage_12v_item = status_dict.FloatStatusItem(name='voltage-12V', column_name='value',
                                                   nominal_range=status_dict.Range(10, 15), good_range=None,
                                                   warning_range=None)
    voltage_12v_filewatcher = status_dict.StatusFileWatcher(name='voltage_12v_filewatcher', items=[voltage_12v_item],
                                                            filename_glob=path)

    path = '/var/lib/collectd/csv/pmc-camera-?.unassigned-domain/ipmi/temperature-CPU Temp processor (3.1)-*'
    temp_cpu_item = status_dict.FloatStatusItem(name='temp_cpu', column_name='value',
                                                nominal_range=status_dict.Range(20, 60), good_range=None,
                                                warning_range=None)
    temp_cpu_filewatcher = status_dict.StatusFileWatcher(name='temp_cpu_filewatcher', items=[temp_cpu_item],
                                                         filename_glob=path)

    test_multifilewatcher = status_dict.MultiStatusFileWatcher('test_multi_filewatcher',
                                                              [voltage_12v_filewatcher, temp_cpu_filewatcher])

    path = '/home/pmc/logs/housekeeping/charge_controller/pmc-charge-controller-?_*[!eeprom].csv'

    battery_voltage = status_dict.FloatStatusItem(name='battery_voltage', column_name='register_25',
                                                  nominal_range=status_dict.Range(0, 1000), good_range=None,
                                                  warning_range=None)
    array_voltage = status_dict.FloatStatusItem(name='array_voltage', column_name='register_28',
                                                nominal_range=status_dict.Range(0, 1000), good_range=None,
                                                warning_range=None)
    charge_controller_filewatcher = status_dict.StatusFileWatcher(name='charge_controller_filewatcher',
                                                                  items=[battery_voltage, array_voltage],
                                                                  filename_glob=path)

    return status_dict.StatusGroup('mygroup', [test_multifilewatcher, charge_controller_filewatcher])
    # [temp_cpu_filewatcher, voltage_12v_filewatcher, charge_controller_filewatcher])


def setup_logger():
    logger = logging.getLogger('pmc_camera')
    default_handler = logging.StreamHandler()

    message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
    default_formatter = logging.Formatter(message_format)
    default_handler.setFormatter(default_formatter)
    logger.addHandler(default_handler)
    logger.setLevel(logging.DEBUG)
    return logger


def main():
    logger = setup_logger()
    mygroup = setup_group()
    while True:
        mygroup.update()
        logger.debug('%r' % mygroup.get_status())
        time.sleep(5)


if __name__ == "__main__":
    main()

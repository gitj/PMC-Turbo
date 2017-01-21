from pmc_camera.communication import status_dict
import logging
import time

year_month_day = time.strftime('%Y-%m-%d')

voltage_12v_item = status_dict.FloatStatusItem(name='vim_voltage-12V', column_name='value',
                                               nominal_range=status_dict.Range(10, 15), good_range=None,
                                               warning_range=None)

path = '/var/lib/collectd/csv/pmc-camera-0.unassigned-domain/ipmi/voltage-12V system_board (7.17)-' + year_month_day  # 2017-01-21'

voltage_12v_filewatcher = status_dict.StatusFileWatcher(name='voltage_12v_filewatcher', items=[voltage_12v_item],
                                                        filename=path)

temp_cpu_item = status_dict.FloatStatusItem(name='temp_cpu', column_name='value',
                                            nominal_range=status_dict.Range(20, 60), good_range=None,
                                            warning_range=None)

path = '/var/lib/collectd/csv/pmc-camera-0.unassigned-domain/ipmi/temperature-CPU Temp processor (3.1)-' + year_month_day  # 2017-01-21'

temp_cpu_filewatcher = status_dict.StatusFileWatcher(name='temp_cpu_filewatcher', items=[temp_cpu_item],
                                                     filename=path)

mygroup = status_dict.StatusGroup('mygroup', [temp_cpu_filewatcher, voltage_12v_filewatcher])


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
    while True:
        mygroup.update()
        logger.debug('%r' % mygroup.get_status_summary())
        time.sleep(5)


if __name__ == "__main__":
    main()

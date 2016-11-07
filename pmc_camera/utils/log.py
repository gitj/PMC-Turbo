import os
import time
import logging

LOG_DIR='/home/pmc/logs'

long_message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
short_message_format = '%(levelname)-4.4s %(asctime)s - %(funcName)s:%(lineno)d  %(message)s'
default_handler = logging.StreamHandler()
default_formatter = logging.Formatter(short_message_format)
long_formatter = logging.Formatter(long_message_format)
default_handler.setFormatter(default_formatter)


def file_handler(name='', level=logging.DEBUG):
    """
    Return a FileHandler that will write to a log file in the default location with a sensible name.

    Parameters
    ----------
    name : str
        A name to identify the log file; a good practice would be to use __file__ from the calling module.
    level : int
        The log level to use.

    Returns
    -------
    logging.FileHandler
    """
    fh = logging.FileHandler(os.path.join(LOG_DIR, '.'.join([time.strftime('%Y-%m-%d_%H%M%S'), name.replace('/','.'),
                                                             'log'])))
    fh.setFormatter(long_formatter)
    fh.setLevel(level)
    return fh
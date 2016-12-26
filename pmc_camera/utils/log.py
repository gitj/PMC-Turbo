import os
import time
import logging

LOG_DIR = '/home/pmc/logs'

long_message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
short_message_format = '%(levelname)-4.4s %(asctime)s - %(funcName)s:%(lineno)d  %(message)s'
default_handler = logging.StreamHandler()
default_formatter = logging.Formatter(short_message_format)
long_formatter = logging.Formatter(long_message_format)
default_handler.setFormatter(default_formatter)

pmc_camera_logger = logging.getLogger('pmc_camera')
ground_logger = logging.getLogger('ground')


def setup_stream_handler(level=logging.INFO):
    for logger in [pmc_camera_logger, ground_logger]:
        if default_handler not in logger.handlers:
            logger.addHandler(default_handler)
            default_handler.setLevel(level)
            logger.setLevel(level)
        logger.info("Stream handler initialized")


def setup_file_handler(level=logging.DEBUG):
    for name,logger in [('pmc_camera',pmc_camera_logger), ('ground',ground_logger)]:
        has_file_handler = False
        for handler in logger.handlers:
            if issubclass(handler.__class__, logging.FileHandler):
                has_file_handler = True
        if not has_file_handler:
            logger.addHandler(file_handler(name, level))
            logger.info("File handler added")
            logger.setLevel(level)
        logger.info("File handler initialized")


def file_handler(name='', level=logging.DEBUG):
    """
    Return a FileHandler that will write to a log file in the default location with a sensible name.

    Parameters
    ----------
    name : str
        A name to identify the log file
    level : int
        The log level to use.

    Returns
    -------
    logging.FileHandler
    """
    fh = logging.FileHandler(os.path.join(LOG_DIR, '.'.join([time.strftime('%Y-%m-%d_%H%M%S'), name.replace('/', '.'),
                                                             'log'])))
    fh.setFormatter(long_formatter)
    fh.setLevel(level)
    return fh

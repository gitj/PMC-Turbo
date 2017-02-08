import os
import time
import logging
import subprocess
try:
    from coloredlogs import ColoredFormatter
except ImportError:
    ColoredFormatter = logging.Formatter

LOG_DIR = '/home/pmc/logs'

long_message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
short_message_format = '%(levelname)-4.4s %(asctime)s - %(funcName)s:%(lineno)d  %(message)s'
default_handler = logging.StreamHandler()
default_formatter = ColoredFormatter(short_message_format)
long_formatter = logging.Formatter(long_message_format)
default_handler.setFormatter(default_formatter)

pmc_camera_logger = logging.getLogger('pmc_turbo')
pmc_camera_logger.setLevel(logging.DEBUG)
ground_logger = logging.getLogger('pmc_turbo')
ground_logger.setLevel(logging.DEBUG)

KNOWN_LOGGERS = {'pipeline': pmc_camera_logger,
                   'communicator': pmc_camera_logger,
                   'controller': pmc_camera_logger,
                   'gse_receiver': ground_logger,
                   }

def setup_stream_handler(level=logging.INFO):
    for logger in [pmc_camera_logger, ground_logger]:
        if default_handler not in logger.handlers:
            logger.addHandler(default_handler)
            default_handler.setLevel(level)
            logger.info("Stream handler initialized for %s" % logger.name)


def setup_file_handler(name, level=logging.DEBUG, logger=None):
    try:
        logger = KNOWN_LOGGERS[name]
        warning = ''
    except KeyError:
        if logger is None:
            raise ValueError("Unknown logger name %s and no logger explicitly provided" % name)
        warning = 'Unknown logger %s being initialized, please update %s with this logger' % (name,__name__)
    has_file_handler = False
    for handler in logger.handlers:
        if issubclass(handler.__class__, logging.FileHandler):
            has_file_handler = True
    if not has_file_handler:
        logger.addHandler(file_handler(name, level))
        logger.info("File handler added and initialized for %s" % name)
        logger.info(git_log())
        logger.info(git_status())
    if warning:
        logger.warning(warning)


def file_handler(name, level=logging.DEBUG):
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
    fh = logging.FileHandler(os.path.join(LOG_DIR, '.'.join([name.replace('/', '.'), time.strftime('%Y-%m-%d_%H%M%S'),
                                                             'log'])))
    fh.setFormatter(long_formatter)
    fh.setLevel(level)
    return fh

def git_log():
    code_directory = os.path.dirname(os.path.abspath(__file__))
    try:
        return subprocess.check_output(("cd {}; git log -1".format(code_directory)), shell=True)
    except Exception as e:
        return str(e)


def git_status():
    code_directory = os.path.dirname(os.path.abspath(__file__))
    try:
        return subprocess.check_output(("cd {}; git status --porcelain".format(code_directory)), shell=True)
    except Exception as e:
        return str(e)

def git_hash(short=True):
    if short:
        short_param = '--short'
    else:
        short_param = ''
    code_directory = os.path.dirname(os.path.abspath(__file__))
    try:
        return subprocess.check_output(("cd {}; git rev-parse {} HEAD".format(code_directory,short_param)),
                                       shell=True).strip()
    except Exception as e:
        return str(e)

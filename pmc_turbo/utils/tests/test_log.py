from nose.tools import assert_raises

from pmc_turbo.utils import log


def test_git_functions():
    log.git_hash()
    log.git_hash(short=False)
    log.git_status()
    log.git_log()

def test_log_functions():
    log.LOG_DIR = '/tmp'
    log.setup_stream_handler()
    log.setup_file_handler('pipeline')
    log.setup_file_handler('controller')
    log.setup_file_handler('communicator')
    log.setup_file_handler('gse_receiver')
    with assert_raises(ValueError):
        log.setup_file_handler('unknown')
    log.setup_file_handler('known_unknown', logger=log.pmc_turbo_logger)



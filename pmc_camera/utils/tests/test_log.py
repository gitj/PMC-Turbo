from pmc_camera.utils import log

def test_git_functions():
    log.git_hash()
    log.git_hash(short=False)
    log.git_status()
    log.git_log()
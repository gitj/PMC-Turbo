import shutil
import tempfile
import threading
import time
import os

from traitlets.config.loader import load_pyconfig_files

from nose.tools import timed

from pmc_turbo.camera.pipeline import basic_pipeline
from pmc_turbo.utils.configuration import default_config_dir

print "default config dir",default_config_dir
basic_config = load_pyconfig_files(['no_hardware.py'], default_config_dir)
assert basic_config
print "loaded config",basic_config

def setup_module():
    counter_dir = tempfile.mkdtemp()
    disk_dirs = [tempfile.mkdtemp() for k in range(4)]
    basic_config.GlobalConfiguration.log_dir = tempfile.mkdtemp()

    basic_config.GlobalConfiguration.housekeeping_dir = os.path.join(basic_config.GlobalConfiguration.log_dir,'housekeeping')
    basic_config.GlobalConfiguration.counters_dir = os.path.join(basic_config.GlobalConfiguration.log_dir,'counters')

def teardown_module():
    shutil.rmtree(basic_config.GlobalConfiguration.log_dir)

@timed(20)
def test_pipeline_runs():
    config = basic_config.copy()
    config.BasicPipeline.default_write_enable=1
    bpl = basic_pipeline.BasicPipeline(config=config)

    bpl.initialize()
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    tag = bpl.send_camera_command("ExposureTimeAbs","10000")
    name,value,result,gate_time = bpl.send_camera_command_get_result("ExposureTimeAbs","1000",timeout=5)
    name,value,result,gate_time = bpl.get_camera_command_result(tag)
    time.sleep(1)
    bpl.close()

@timed(20)
def test_pipeline_runs_no_disk():
    config = basic_config.copy()
    config.BasicPipeline.default_write_enable=0
    bpl = basic_pipeline.BasicPipeline(config=basic_config)
    bpl.initialize()
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    time.sleep(1)
    bpl.close()

if __name__ == "__main__":
    import pmc_turbo.utils.log
    import logging
    pmc_turbo.utils.log.setup_stream_handler(logging.DEBUG)
    test_pipeline_runs()
    test_pipeline_runs_no_disk()
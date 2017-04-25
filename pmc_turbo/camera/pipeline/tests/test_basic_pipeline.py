import shutil
import tempfile
import threading
import time

from nose.tools import timed

from pmc_turbo.camera.pipeline import basic_pipeline
from pmc_turbo.utils.tests import test_config
harness = test_config.BasicTestHarness()
harness.setup()
basic_config = harness.basic_config
assert basic_config
print "loaded config",basic_config

def teardown_module():
    harness.teardown()

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
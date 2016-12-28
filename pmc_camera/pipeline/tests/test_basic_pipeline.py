import time
import threading
import tempfile
import shutil
from nose.tools import timed
from pmc_camera.pipeline import basic_pipeline

@timed(20)
def test_pipeline_runs():
    tempdir = tempfile.mkdtemp()
    bpl = basic_pipeline.BasicPipeline(disks_to_use=[tempdir],use_simulated_camera=True)
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    print "pyro thread started"
    time.sleep(1)
    bpl.get_status()
    print "got status"
    tag = bpl.send_camera_command("ExposureTimeAbs","10000")
    print "sent command"
    name,value,result,gate_time = bpl.send_camera_command_get_result("ExposureTimeAbs","1000",timeout=2)
    print "sent command, got result"
    name,value,result,gate_time = bpl.get_camera_command_result(tag)
    print "got command result"
    time.sleep(1)
    bpl.close()
    shutil.rmtree(tempdir)
    print "shut down"

@timed(20)
def test_pipeline_runs_no_disk():
    tempdir = tempfile.mkdtemp()
    bpl = basic_pipeline.BasicPipeline(disks_to_use=[tempdir],use_simulated_camera=True,default_write_enable=0)
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    time.sleep(1)
    bpl.close()
    shutil.rmtree(tempdir)

if __name__ == "__main__":
    import pmc_camera.utils.log
    import logging
    pmc_camera.utils.log.setup_stream_handler(logging.DEBUG)
    test_pipeline_runs()
    test_pipeline_runs_no_disk()
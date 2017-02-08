import shutil
import tempfile
import threading
import time

from nose.tools import timed

from pmc_turbo.camera.pipeline import basic_pipeline

fake_pipeline_port = 45677

@timed(20)
def test_pipeline_runs():
    counter_dir = tempfile.mkdtemp('pipeline_counters')
    tempdir = tempfile.mkdtemp()
    bpl = basic_pipeline.BasicPipeline(disks_to_use=[tempdir], use_simulated_camera=True,
                                       pipeline_port=fake_pipeline_port, counter_dir=counter_dir)
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    tag = bpl.send_camera_command("ExposureTimeAbs","10000")
    name,value,result,gate_time = bpl.send_camera_command_get_result("ExposureTimeAbs","1000",timeout=2)
    name,value,result,gate_time = bpl.get_camera_command_result(tag)
    time.sleep(1)
    bpl.close()
    shutil.rmtree(tempdir)
    shutil.rmtree(counter_dir)

@timed(20)
def test_pipeline_runs_no_disk():
    counter_dir = tempfile.mkdtemp('pipeline_counters')
    tempdir = tempfile.mkdtemp()
    bpl = basic_pipeline.BasicPipeline(disks_to_use=[tempdir], use_simulated_camera=True, default_write_enable=0,
                                       pipeline_port=fake_pipeline_port, counter_dir=counter_dir)
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    time.sleep(1)
    bpl.close()
    shutil.rmtree(tempdir)
    shutil.rmtree(counter_dir)

if __name__ == "__main__":
    import pmc_turbo.camera.utils.log
    import logging
    pmc_turbo.camera.utils.log.setup_stream_handler(logging.DEBUG)
    test_pipeline_runs()
    test_pipeline_runs_no_disk()
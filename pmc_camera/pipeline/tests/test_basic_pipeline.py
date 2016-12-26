import time
import threading
from pmc_camera.pipeline import basic_pipeline
def test_pipeline_runs():
    bpl = basic_pipeline.BasicPipeline(disks_to_use=['/tmp'],use_simulated_camera=True)
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

def test_pipeline_runs_no_disk():
    bpl = basic_pipeline.BasicPipeline(disks_to_use=['/tmp'],use_simulated_camera=True,default_write_enable=0)
    thread = threading.Thread(target=bpl.run_pyro_loop)
    thread.daemon=True
    thread.start()
    time.sleep(1)
    bpl.get_status()
    time.sleep(1)
    bpl.close()

if __name__ == "__main__":
    import pmc_camera.utils.log
    import logging
    pmc_camera.utils.log.setup_stream_handler(logging.DEBUG)
    test_pipeline_runs()
    test_pipeline_runs_no_disk()
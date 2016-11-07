import time
from pmc_camera.pipeline import basic_pipeline

def test_pipeline_runs():
    bpl = basic_pipeline.BasicPipeline(disks_to_use=['/tmp'],use_simulated_camera=True)
    time.sleep(1)
    bpl.get_status()
    bpl.close()

def test_pipeline_runs_no_disk():
    bpl = basic_pipeline.BasicPipeline(disks_to_use=['/tmp'],use_simulated_camera=True,default_write_enable=0)
    time.sleep(1)
    bpl.get_status()
    bpl.close()

if __name__ == "__main__":
    test_pipeline_runs()
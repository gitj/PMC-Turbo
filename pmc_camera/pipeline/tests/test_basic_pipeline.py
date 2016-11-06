import time
from pmc_camera.pipeline import basic_pipeline

def test_pipeline_runs():
    bpl = basic_pipeline.BasicPipeline(disks_to_use=['/tmp'],use_simulated_camera=True)
    time.sleep(1)
    bpl.get_status()
    bpl.close()
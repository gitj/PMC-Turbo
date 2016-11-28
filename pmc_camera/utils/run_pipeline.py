from pmc_camera.pipeline.basic_pipeline import BasicPipeline
import time

if __name__ == "__main__":
    bpl = BasicPipeline(disks_to_use=['/data1','/data2','/data3','/data4'],default_write_enable=1)
    bpl.run_pyro_loop()
import logging
from pmc_camera.pipeline.basic_pipeline import BasicPipeline
import pmc_camera.utils.log
import time
import signal


if __name__ == "__main__":
    pmc_camera.utils.log.setup_stream_handler()
    pmc_camera.utils.log.setup_file_handler()
    bpl = BasicPipeline(disks_to_use=['/data1','/data2','/data3','/data4'],default_write_enable=1)
    signal.signal(signal.SIGTERM,bpl.exit)
    bpl.run_pyro_loop()
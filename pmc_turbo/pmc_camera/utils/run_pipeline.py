import signal

from pmc_turbo.pmc_camera.pipeline.basic_pipeline import BasicPipeline

if __name__ == "__main__":
    logger = pmc_turbo.pmc_camera.utils.log.pmc_camera_logger
    pmc_turbo.pmc_camera.utils.log.setup_stream_handler()
    pmc_turbo.pmc_camera.utils.log.setup_file_handler('pipeline')
    bpl = BasicPipeline(disks_to_use=['/data1','/data2','/data3','/data4'],default_write_enable=1)
    signal.signal(signal.SIGTERM,bpl.exit)
    bpl.run_pyro_loop()
import signal
from traitlets.config import Application
from traitlets import Unicode,List

from pmc_turbo.camera.pipeline.basic_pipeline import BasicPipeline, AcquireImagesProcess, WriteImageProcess
import pmc_turbo.utils.log


class PipelineApp(Application):
    config_file = Unicode(u'', help="Load this config file").tag(config=True)
    write_default_config = Unicode(u'', help="Write template config file to this location").tag(config=True)
    classes = List([BasicPipeline, AcquireImagesProcess])
    aliases = dict(generate_config='PipelineApp.write_default_config')
    def initialize(self, argv=None):
        self.parse_command_line(argv)
        if self.write_default_config:
            with open(self.write_default_config,'w') as fh:
                fh.write(self.generate_config_file())
                self.exit()
        if self.config_file:
            self.load_config_file(self.config_file)
        self.pipeline = BasicPipeline(config=self.config)
        signal.signal(signal.SIGTERM, self.pipeline.exit)
        self.pipeline.initialize()

    def start(self):
        self.pipeline.run_pyro_loop()


if __name__ == "__main__":

    pmc_turbo.utils.log.setup_stream_handler(level = pmc_turbo.utils.log.logging.DEBUG)
    pmc_turbo.utils.log.setup_file_handler('pipeline')
    app = PipelineApp()
    app.initialize()
    app.start()
    #    bpl = BasicPipeline(disks_to_use=['/data1','/data2','/data3','/data4'],default_write_enable=1)
    #    signal.signal(signal.SIGTERM,bpl.exit)
    #    bpl.run_pyro_loop()

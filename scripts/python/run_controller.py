import os
import sys
import pmc_turbo
from traitlets.config import Application
from traitlets import Unicode,List
import logging

from pmc_turbo.camera.pipeline.controller import Controller

import pmc_turbo.utils.log
from pmc_turbo.utils.configuration import default_config_dir


class ControllerApp(Application):
    config_file = Unicode(os.path.join(default_config_dir,'default_balloon.py'), help="Load this config file").tag(config=True)
    config_dir = Unicode(default_config_dir, help="Config file directory").tag(config=True)
    write_default_config = Unicode(u'', help="Write template config file to this location").tag(config=True)
    classes = List([Controller])
    aliases = dict(generate_config='ControllerApp.write_default_config',
                   config_file='ControllerApp.config_file')
    log_level = logging.DEBUG
    def initialize(self, argv=None):
        print "initializing controller with arguments:",argv
        self.raise_config_file_errors = True
        self.parse_command_line(argv)
        if self.write_default_config:
            with open(self.write_default_config,'w') as fh:
                fh.write(self.generate_config_file())
                self.exit()
        if self.config_file:
            print 'loading config: ', self.config_dir, self.config_file
            self.load_config_file(self.config_file, path=self.config_dir)
        print "configuration",self.config
        self.controller = Controller(config=self.config)

    def start(self):
        self.controller.setup_pyro_daemon()
        while True:
            self.controller.main_loop()


if __name__ == "__main__":

    pmc_turbo.utils.log.setup_stream_handler(level = pmc_turbo.utils.log.logging.DEBUG)
    pmc_turbo.utils.log.setup_file_handler('controller')
    app = ControllerApp()
    app.initialize(sys.argv)
    app.start()

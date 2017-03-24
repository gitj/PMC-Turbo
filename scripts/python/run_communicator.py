import logging
import os
from pmc_turbo.communication import camera_communicator
from pmc_turbo.communication import housekeeping_classes
from pmc_turbo.utils import log
from pmc_turbo.utils import camera_id
from pmc_turbo.utils import startup_script_constants
from traitlets import Int, Unicode, Bool, List, Float, Tuple, Bytes, TCPAddress, Dict
from traitlets.config import Application
from traitlets.config.loader import load_pyconfig_files
from pmc_turbo.utils.configuration import default_config_dir

#basic_config = load_pyconfig_files(['default_balloon.py'], default_config_dir)

class CommunicatorApp(Application):
    config_file = Unicode(u'default_balloon.py', help="Load this config file").tag(config=True)
    config_dir = Unicode(default_config_dir, help="Config file directory").tag(config=True)
    write_default_config = Unicode(u'', help="Write template config file to this location").tag(config=True)
    classes = List([camera_communicator.Communicator])
    aliases = dict(generate_config='CommunicatorApp.write_default_config',
                   config_file='CommunicatorApp.config_file')
    address_book = Dict(default_value={0: ('0.0.0.0', 40000)},
                        help='Dict for mapping camera ID to Pyro address.'
                             'e.g. {3: ("pmc-camera-3", 40000)}').tag(config=True)

    def initialize(self, argv=None):
        self.parse_command_line(argv)
        if self.write_default_config:
            with open(self.write_default_config, 'w') as fh:
                fh.write(self.generate_config_file())
                self.exit()
        if self.config_file:
            print 'loading config: ', self.config_dir, self.config_file
            self.load_config_file(self.config_file, path=self.config_dir)
        #self.update_config(basic_config)
        print self.config
        cam_id = camera_id.get_camera_id()
        pyro_port = self.address_book[cam_id][1]
        sorted_keys = self.address_book.keys()
        sorted_keys.sort()
        peers = ['PYRO:communicator@%s:%d' % self.address_book[key] for key in sorted_keys]

        start_as_leader = (cam_id == 0)

        self.communicator = camera_communicator.Communicator(cam_id=cam_id, peers=peers, controller=None, leader=start_as_leader,
                                                             pyro_port=pyro_port, config=self.config)

    def start(self):
        group = housekeeping_classes.construct_super_group_from_json_list(startup_script_constants.JSON_PATHS)
        self.communicator.add_status_group(group)
        self.communicator.setup_pyro_daemon()
        self.communicator.start_pyro_thread()
        self.communicator.main_loop()


if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('communicator')
    app = CommunicatorApp()
    app.initialize()
    app.start()

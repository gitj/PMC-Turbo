import time
import os
import logging
from traitlets import (Int, Bytes, Float, Union, List, Tuple, Enum)
import pmc_turbo
import Pyro4
from pmc_turbo.ground.ground_configuration import GroundConfiguration, standard_baudrates
from pmc_turbo.ground.gse_receiver import GSEReceiver

logger = logging.getLogger(__name__)

OPENPORT = 'openport'
GSE_SIP = 'gse_sip'
LOS = 'los'
TDRSS_DIRECT = 'tdrss_direct'

@Pyro4.expose
class GSEReceiverManager(GroundConfiguration):
    downlinks_to_use = List(Enum((OPENPORT,GSE_SIP,LOS,TDRSS_DIRECT)),
                            default_value=['openport','gse_sip', 'los'],
                            help="Downlinks to setup and use.").tag(config=True)
    receiver_main_loop_interval = Float(1.0,min=0).tag(config=True)
    root_data_path = Bytes('/data/gse_data').tag(config=True)
    def __init__(self, **kwargs):
        super(GSEReceiverManager,self).__init__(**kwargs)
        timestring = time.strftime('%Y-%m-%d_%H%M%S')
        self.data_path = os.path.join(self.root_data_path,timestring)
        self.receivers = {}
        for link_name in self.downlinks_to_use:
            parameters = self.downlink_parameters[link_name]
            use_gse_packets = (link_name == GSE_SIP)
            receiver = GSEReceiver(root_path=self.data_path,serial_port_or_socket_port=parameters['port'],
                                                    baudrate=parameters['baudrate'], loop_interval=parameters['loop_interval'],
                                                    use_gse_packets=use_gse_packets,name=link_name)
            log.setup_file_handler(link_name,logger=receiver.logger)
            self.receivers[link_name] = receiver
            receiver.start_main_loop_thread()


if __name__ == "__main__":
    from pmc_turbo.utils import log
    log.setup_stream_handler(logging.DEBUG)
    gserm = GSEReceiverManager()
    daemon = Pyro4.Daemon('0.0.0.0',55000)
    daemon.register(GSEReceiverManager,'gserm')
    daemon.requestLoop()

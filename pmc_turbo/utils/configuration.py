import os

from traitlets import (Bool, Int, CInt, List, Unicode)
from traitlets.config import Configurable
from pmc_turbo import root_dir

default_config_dir = os.path.abspath(os.path.join(root_dir, '../config/balloon'))

# Currently the logging system needs its directory set up separately so that logging can happen while the system
# is being initialized
LOG_DIR = '/home/pmc/logs'


class GlobalConfiguration(Configurable):
    """
    General configuraion parameters used throughot the balloon
    """
    data_directories = List(trait=Unicode, default_value=['/data1', '/data2', '/data3', '/data4']).tag(config=True)
    pipeline_pyro_port = Int(50000, min=1024, max=65535).tag(config=True)
    controller_pyro_port = Int(50001, min=1024, max=65535).tag(config=True)
    log_dir = Unicode('/home/pmc/logs').tag(config=True)
    housekeeping_dir = Unicode('/home/pmc/logs/housekeeping').tag(config=True)
    counters_dir = Unicode('/home/pmc/logs/counters').tag(config=True)


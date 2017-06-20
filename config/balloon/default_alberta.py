import os
from pmc_turbo import root_dir

# noinspection PyUnresolvedReferences
c = get_config()

c.GlobalConfiguration.data_directories = ['/data1', '/data2', '/data3', '/data4']

c.BasicPipeline.num_data_buffers = 16

housekeeping_dir = '/var/pmclogs/housekeeping'

c.PipelineApp.housekeeping_dir = housekeeping_dir
c.PipelineApp.counters_dir = os.path.join(housekeeping_dir, 'counters')

# ------------------------------------------------------------------------------
# CommunicatorApp(Application) configuration
# ------------------------------------------------------------------------------

c.Application.log_level = 0

## This is an application.

## Dict for mapping camera ID to Pyro address.e.g. {3: ("pmc-camera-3", 40000)}
c.CommunicatorApp.address_book = {0: ('pmc-camera-0', 40000), 1: ('pmc-camera-1', 40000),
                                  2: ('pmc-camera-2', 40000), 3: ('pmc-camera-3', 40000),
                                  4: ('pmc-camera-4', 40000), 5: ('pmc-camera-5', 40000),
                                  6: ('pmc-camera-6', 40000), 7: ('pmc-camera-7', 40000)}

c.GlobalConfiguration.controller_pyro_port = 50001

##
c.GlobalConfiguration.counters_dir = '/var/pmclogs/counters'

##
c.GlobalConfiguration.housekeeping_dir = '/var/pmclogs/housekeeping'

##
c.GlobalConfiguration.log_dir = '/var/pmclogs'

##
c.GlobalConfiguration.pipeline_pyro_port = 50000

c.Controller.main_loop_interval = 1.0

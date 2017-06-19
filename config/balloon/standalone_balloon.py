import os
from pmc_turbo import root_dir

from pmc_turbo.utils.camera_id import get_camera_id

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
camera_id = get_camera_id()
if camera_id >= 8:
    raise Exception("Invalid camera_id: %r! This config file can only be used on a pmc-camera- machine.")
c.CommunicatorApp.address_book = {camera_id: (('pmc-camera-%d' % camera_id), 40000)}

c.GlobalConfiguration.controller_pyro_port = 50001

##
c.GlobalConfiguration.counters_dir = '/var/pmclogs/counters'

##
c.GlobalConfiguration.housekeeping_dir = '/var/pmclogs/housekeeping'

##
c.GlobalConfiguration.log_dir = '/var/pmclogs'

##
c.GlobalConfiguration.pipeline_pyro_port = 50000

# ------------------------------------------------------------------------------
# Communicator(GlobalConfiguration) configuration
# ------------------------------------------------------------------------------

## List of tuples - hirate downlink name, Enum(("openport", "highrate", "los"))
#  hirate downlink address,
#  hirate downlink downlink speed in bytes per second. 0 means link is disabled.
#  e.g. [("openport", ("192.168.1.70", 4501), 10000), ...]
openport_destination_ip = '192.168.1.70'
c.Communicator.hirate_link_parameters = [('openport', (openport_destination_ip, 4501), 100),
                                         ]

## List of tuples - name, lowrate downlink address and lowrate uplink port.e.g.
#  [("comm1", ("pmc-serial-1", 5001), 5001), ...]
c.Communicator.lowrate_link_parameters = [("openport", (openport_destination_ip,5001), 5001)]

c.Communicator.charge_controller_settings = []

c.Communicator.battery_monitor_port = ""
##
c.Communicator.initial_peer_polling_order = [get_camera_id()]

c.Communicator.peers_with_battery_monitors = [4]

c.Communicator.narrowfield_cameras = [4]
c.Communicator.widefield_cameras = []

##
c.Communicator.loop_interval = 0.01


##
c.Communicator.use_controller = True


JSON_FILENAMES = [
    'camera_items.json',
    'charge_controller_register_items.json',
    'charge_controller_eeprom_items.json',
    'counter_items.json',
    'collectd_items.json',
    'labjack_items.json'
]

c.Communicator.json_paths = [os.path.join(os.path.split(root_dir)[0], 'status_item_params', json_fn) for json_fn in JSON_FILENAMES]
c.Communicator.filewatcher_threshhold_time = 60.

# This should not live here, but it will until I decide where to move it.

from pmc_turbo.utils import camera_id

PIPELINE_IP = '0.0.0.0'
PIPELINE_PORT = 50000

HOST_IP = '0.0.0.0'
CONTROLLER_IP = 50001

CONTROLLER_NAME = 'image'

CAM_ID = camera_id.get_camera_id()
if CAM_ID == 255:
    raise ValueError('CAM_ID is 255 - error in get_camera_id')

if CAM_ID == 0:
    LEADER = True
else:
    LEADER = False

if False:
    PEER_URIS = ['PYRO:communicator@0.0.0.0:40000',
                 'PYRO:communicator@0.0.0.0:40001',
                 'PYRO:communicator@0.0.0.0:40002',
                 'PYRO:communicator@0.0.0.0:40003',
                 'PYRO:communicator@0.0.0.0:40004',
                 'PYRO:communicator@0.0.0.0:40005',
                 'PYRO:communicator@0.0.0.0:40006',
                 'PYRO:communicator@0.0.0.0:40007']
if True:
    PEER_URIS = ['PYRO:communicator@0.0.0.0:40000',
                 'PYRO:communicator@pmc-camera-1:40000',
                 'PYRO:communicator@pmc-camera-2:40000',
                 'PYRO:communicator@pmc-camera-3:40000',
                 'PYRO:communicator@pmc-camera-4:40000',
                 'PYRO:communicator@pmc-camera-5:40000',
                 'PYRO:communicator@pmc-camera-6:40000',
                 'PYRO:communicator@pmc-camera-7:40000', ]

PEER_POLLING_ORDER = [0, 1, 2, 3, 4, 5, 6, 7]

CONTROLLER_URI = 'PYRO:image@192.168.1.30:50001'

LOOP_INTERVAL = 0.01

LOWRATE_UPLINK_PORT = 5001
LOWRATE_DOWNLINK_IP, LOWRATE_DOWNLINK_PORT = 'pmc-serial-1', 5001

TDRSS_HIRATE_DOWNLINK_IP, TDRSS_HIRATE_DOWNLINK_PORT = 'pmc-serial-1', 5002

TDRSS_DOWNLINK_SPEED = 700

OPENPORT_DOWNLINK_IP = '192.168.1.70'
OPENPORT_DOWNLINK_PORT = 4501
OPENPORT_DOWNLINK_SPEED = 10000

GROUP_NAME = 'supergroup'

CSV_PATHS_AND_PREAMBLES = [('/home/pmc/camera_items.csv', '/var/lib/collectd/csv/*/'),
                           ('/home/pmc/charge_controller_items.csv', ''), ]
# ('/home/pmc/collectd_items.csv', '/var/lib/collectd/csv/*/')]

JSON_PATHS = ['/home/pmc/pmchome/pmc-turbo/status_item_params/camera_items.json',
              '/home/pmc/pmchome/pmc-turbo/status_item_params/charge_controller_items.json']
JSON_RANGE_PATHS = ['/home/pmc/pmchome/pmc-turbo/status_item_params/camera_items_ranges.json',
                    '/home/pmc/pmchome/pmc-turbo/status_item_params/charge_controller_items_ranges.json']

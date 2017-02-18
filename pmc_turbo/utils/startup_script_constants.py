# This should not live here, but it will until I decide where to move it.

PIPELINE_IP = '0.0.0.0'
PIPELINE_PORT = 50000

HOST_IP = '0.0.0.0'
CONTROLLER_IP = 50001

CONTROLLER_NAME = 'image'

CAM_ID = 0

LEADER = True

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

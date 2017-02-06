# This should not live here, but it will until I decide where to move it.

from pmc_camera.communication import aggregator_hard_coded

PIPELINE_IP = '0.0.0.0'
PIPELINE_PORT = 50000

HOST_IP = '0.0.0.0'
CONTROLLER_IP = 50001

CONTROLLER_NAME = 'image'

CAM_ID = 0

LEADER = True

PEER_URIS = ['PYRO:communicator@0.0.0.0:40000', 'PYRO:communicator@0.0.0.0:40001', 'PYRO:communicator@0.0.0.0:40002',
             'PYRO:communicator@0.0.0.0:40003', 'PYRO:communicator@0.0.0.0:40004', 'PYRO:communicator@0.0.0.0:40005',
             'PYRO:communicator@0.0.0.0:40006', 'PYRO:communicator@0.0.0.0:40007']

PEER_POLLING_ORDER = [0, 1, 2, 3, 4, 5, 6, 7]

CONTROLLER_URI = 'PYRO:image@192.168.1.30:50001'

LOWRATE_UPLINK_PORT = 4001
LOWRATE_DOWNLINK_IP, LOWRATE_DOWNLINK_PORT = 'pmc-serial-0', 4001

HIRATE_DOWNLINK_IP, HIRATE_DOWNLINK_PORT = 'pmc-serial-0', 4002

DOWNLINK_SPEED = 700

GROUP_NAME = 'supergroup'

CSV_PATHS_AND_PREAMBLES = [('/home/pmc/pmchome/pmc-turbo/pmc_camera/communication/camera_items.csv', ''),
                           ('/home/pmc/pmchome/pmc-turbo/pmc_camera/communication/charge_controller_items.csv', ''),
                           ('/home/pmc/pmchome/pmc-turbo/pmc_camera/communication/collectd_items.csv',
                            '/var/lib/collectd/csv/*/')]
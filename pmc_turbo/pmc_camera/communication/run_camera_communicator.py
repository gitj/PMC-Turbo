import logging
import os
import time

from pmc_turbo.pmc_camera.communication import camera_communicator, aggregator_hard_coded

from pmc_turbo.pmc_camera.communication import housekeeping_classes


def setup_logger():
    logger = logging.getLogger('pmc_camera')
    default_handler = logging.StreamHandler()

    LOG_DIR = '/home/pmc/logs/camera_communicator'
    filename = os.path.join(LOG_DIR, (time.strftime('%Y-%m-%d_%H%M%S.txt')))
    default_filehandler = logging.FileHandler(filename=filename)

    message_format = '%(levelname)-8.8s %(asctime)s - %(name)s.%(funcName)s:%(lineno)d  %(message)s'
    default_formatter = logging.Formatter(message_format)
    default_handler.setFormatter(default_formatter)
    default_filehandler.setFormatter(default_formatter)
    logger.addHandler(default_handler)
    logger.addHandler(default_filehandler)
    logger.setLevel(logging.DEBUG)


def run_communicator(cam_id, peers, controller, leader, peer_polling_order=[]):
    setup_logger()
    UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT = 4001, '192.168.1.54', 4001
    c = camera_communicator.Communicator(cam_id, peers, controller)
    if peer_polling_order:
        c.set_peer_polling_order(peer_polling_order)
    if leader:
        c.setup_links(UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT, '192.168.1.54', 4002, 700)
        c.setup_aggregator(aggregator_hard_coded.setup_group())

        csv_paths_and_preambles = [('camera_items.csv', ''),
                                   ('charge_controller_items.csv', ''),
                                   ('collectd_items.csv', '/var/lib/collectd/csv/*/')]
        group = housekeeping_classes.construct_super_group_from_csv_list('supergroup', csv_paths_and_preambles)
        c.add_status_group(group)

        c.start_leader_thread()


def two_camera_leader():
    # run_communicator(cam_id=0, peers=[Pyro4.Proxy('PYRO:communicator@0.0.0.0:40000'),
    #                                  Pyro4.Proxy('PYRO:communicator@0.0.0.0:40001')],
    #                 controller=Pyro4.Proxy('PYRO:image@192.168.1.30:50001'), leader=True, peer_polling_order=[0, 1])

    run_communicator(cam_id=0, peers=['PYRO:communicator@0.0.0.0:40000', 'PYRO:communicator@0.0.0.0:40001'],
                     controller='PYRO:image@192.168.1.30:50001', leader=True, peer_polling_order=[0, 1])


def two_camera_follower():
    run_communicator(cam_id=1, peers=[],
                     controller='PYRO:image@192.168.1.30:50002', leader=False)

import IPython
from pmc_camera.communication import camera_communicator
import logging
import os
import time
import Pyro4


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


def main(cam_id, peers, image_server, leader):
    setup_logger()
    UPLINK_IP, UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT = '192.168.1.30', 4001, '192.168.1.54', 4001
    c = camera_communicator.Communicator(cam_id, peers, image_server)
    if leader:
        c.setup_leader_attributes(UPLINK_IP, UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT, '192.168.1.54', 4002, 700)
        c.start_leader_thread()


def two_camera_leader():
    main(cam_id=0, peers=[Pyro4.Proxy('PYRO:communicator@0.0.0.0:40000'),
                          Pyro4.Proxy('PYRO:communicator@0.0.0.0:40001')],
         image_server=Pyro4.Proxy('PYRO:image@192.168.1.30:50001'), leader=True)


def two_camera_follower():
    main(cam_id=1, peers=[],
         image_server=Pyro4.Proxy('PYRO:image@192.168.1.30:50002'), leader=False)


if __name__ == "__main__":
    main()
    IPython.embed()

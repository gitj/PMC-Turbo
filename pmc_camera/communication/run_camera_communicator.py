import IPython
from pmc_camera.communication import camera_communicator
import logging
import os
import time

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

UPLINK_IP, UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT = '192.168.1.30', 4001, '192.168.1.54', 4001


def main():
    c = camera_communicator.Communicator(0)
    c.setup_leader_attributes(UPLINK_IP, UPLINK_PORT, DOWNLINK_IP, DOWNLINK_PORT)
    c.start_leader_thread()
    c.start_pyro_thread()
    IPython.embed()


if __name__ == "__main__":
    main()

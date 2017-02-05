import logging
import time
import os
import IPython
from pmc_camera.communication import camera_communicator, housekeeping_classes
from pmc_camera.utils import startup_script_constants

if __name__ == "__main__":
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

    c = camera_communicator.Communicator(startup_script_constants.CAM_ID, startup_script_constants.PEER_URIS,
                                         startup_script_constants.CONTROLLER_URI)
    c.set_peer_polling_order(startup_script_constants.PEER_POLLING_ORDER)

    if startup_script_constants.LEADER:
        c.setup_links(startup_script_constants.LOWRATE_UPLINK_PORT,
                      startup_script_constants.LOWRATE_DOWNLINK_IP, startup_script_constants.LOWRATE_DOWNLINK_PORT,
                      startup_script_constants.HIRATE_DOWNLINK_IP, startup_script_constants.HIRATE_DOWNLINK_PORT,
                      startup_script_constants.DOWNLINK_SPEED)

        c.setup_aggregator(startup_script_constants.AGGREGATOR_GROUP)

        group = housekeeping_classes.construct_super_group_from_csv_list(startup_script_constants.GROUP_NAME,
                                                                         startup_script_constants.CSV_PATHS_AND_PREAMBLES)
        c.add_status_group(group)

        c.leader_loop()

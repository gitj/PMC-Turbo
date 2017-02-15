import logging
from pmc_turbo.communication import camera_communicator
from pmc_turbo.communication import housekeeping_classes
from pmc_turbo.utils import log
from pmc_turbo.utils import startup_script_constants

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('communicator')

    c = camera_communicator.Communicator(startup_script_constants.CAM_ID, startup_script_constants.PEER_URIS,
                                         startup_script_constants.CONTROLLER_URI)
    c.set_peer_polling_order(startup_script_constants.PEER_POLLING_ORDER)

    if startup_script_constants.LEADER:
        c.setup_links(startup_script_constants.LOWRATE_UPLINK_PORT,
                      startup_script_constants.LOWRATE_DOWNLINK_IP, startup_script_constants.LOWRATE_DOWNLINK_PORT,
                      startup_script_constants.TDRSS_HIRATE_DOWNLINK_IP,
                      startup_script_constants.TDRSS_HIRATE_DOWNLINK_PORT,
                      startup_script_constants.TDRSS_DOWNLINK_SPEED,
                      startup_script_constants.OPENPORT_DOWNLINK_IP, startup_script_constants.OPENPORT_DOWNLINK_PORT,
                      startup_script_constants.OPENPORT_DOWNLINK_SPEED)

        c.tdrss_hirate_downlink.enabled = False

        group = housekeeping_classes.construct_super_group_from_csv_list(startup_script_constants.GROUP_NAME,
                                                                         startup_script_constants.CSV_PATHS_AND_PREAMBLES)
        c.add_status_group(group)

        c.leader_loop()

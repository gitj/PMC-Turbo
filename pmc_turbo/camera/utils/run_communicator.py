from pmc_turbo.camera.communication import camera_communicator, housekeeping_classes
from pmc_turbo.camera.utils import startup_script_constants

from pmc_turbo.camera.utils import log

if __name__ == "__main__":
    log.setup_stream_handler()
    log.setup_file_handler('communicator')

    c = camera_communicator.Communicator(startup_script_constants.CAM_ID, startup_script_constants.PEER_URIS,
                                         startup_script_constants.CONTROLLER_URI)
    c.set_peer_polling_order(startup_script_constants.PEER_POLLING_ORDER)

    if startup_script_constants.LEADER:
        c.setup_links(startup_script_constants.LOWRATE_UPLINK_PORT,
                      startup_script_constants.LOWRATE_DOWNLINK_IP, startup_script_constants.LOWRATE_DOWNLINK_PORT,
                      startup_script_constants.HIRATE_DOWNLINK_IP, startup_script_constants.HIRATE_DOWNLINK_PORT,
                      startup_script_constants.DOWNLINK_SPEED)

        group = housekeeping_classes.construct_super_group_from_csv_list(startup_script_constants.GROUP_NAME,
                                                                         startup_script_constants.CSV_PATHS_AND_PREAMBLES)
        c.add_status_group(group)

        c.leader_loop()

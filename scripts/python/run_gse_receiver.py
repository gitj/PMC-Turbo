import logging
import os
import time
from pmc_turbo.utils import gse_receiver_script_constants

from pmc_turbo.ground import gse_receiver
from pmc_turbo.utils import log

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('gse_receiver')

    path = os.path.join(gse_receiver_script_constants.GSE_DATA_PATH, time.strftime('%Y-%m-%d_%H-%M-%S'))
    g = gse_receiver.GSEReceiver(path=path,
                                 serial_port_or_socket_port=gse_receiver_script_constants.SERIAL_PORT_OR_SOCKET_PORT,
                                 baudrate=gse_receiver_script_constants.BAUDRATE,
                                 loop_interval=gse_receiver_script_constants.LOOP_INTERVAL)
    g.main_loop()

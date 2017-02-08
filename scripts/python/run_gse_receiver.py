import logging
import os
import time

from pmc_turbo.ground import gse_receiver
from pmc_turbo.utils import log

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('gse_receiver')

    path = os.path.join('/home/pmc/pmchome/gse_receiver_data', time.strftime('%Y-%m-%d_%H-%M-%S'))
    g = gse_receiver.GSEReceiver(path=path)
    g.main_loop()

import logging

import Pyro4
from pmc_turbo.camera.pipeline import controller

import pmc_turbo.camera.utils.startup_script_constants
from pmc_turbo.camera.utils import log

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('controller')
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:%s' % (pmc_turbo.camera.utils.startup_script_constants.PIPELINE_IP,
                                                        pmc_turbo.camera.utils.startup_script_constants.PIPELINE_PORT))
    except Exception as e:
        print "failed to connect to pipeline:", e
        pipeline = None

    server = controller.Controller(pipeline)
    daemon = Pyro4.Daemon(host=pmc_turbo.camera.utils.startup_script_constants.HOST_IP, port=pmc_turbo.camera.utils.startup_script_constants.CONTROLLER_IP)
    uri = daemon.register(server, pmc_turbo.camera.utils.startup_script_constants.CONTROLLER_NAME)
    print uri
    daemon.requestLoop()

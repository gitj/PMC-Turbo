from pmc_camera.pipeline import controller
import Pyro4
import logging
from pmc_camera.utils import log
import controller_constants

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:%s' % controller_constants.PIPELINE_IP,
                               controller_constants.PIPELINE_PORT)
    except Exception as e:
        print "failed to connect to pipeline:", e
        pipeline = None

    server = controller.Controller(pipeline)
    daemon = Pyro4.Daemon(host=controller_constants.HOST_IP, port=controller_constants.CONTROLLER_IP)
    uri = daemon.register(server, controller_constants.CONTROLLER_NAME)
    print uri
    daemon.requestLoop()

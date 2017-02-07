from pmc_camera.pipeline import controller
import Pyro4
import logging
from pmc_camera.utils import log
import startup_script_constants

if __name__ == "__main__":
    log.setup_stream_handler(level=logging.DEBUG)
    log.setup_file_handler('controller')
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:%s' % (startup_script_constants.PIPELINE_IP,
                               startup_script_constants.PIPELINE_PORT))
    except Exception as e:
        print "failed to connect to pipeline:", e
        pipeline = None

    server = controller.Controller(pipeline)
    daemon = Pyro4.Daemon(host=startup_script_constants.HOST_IP, port=startup_script_constants.CONTROLLER_IP)
    uri = daemon.register(server, startup_script_constants.CONTROLLER_NAME)
    print uri
    daemon.requestLoop()

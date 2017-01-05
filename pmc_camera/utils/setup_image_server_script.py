from pmc_camera.pipeline import simple_image_server
import Pyro4
import logging


def setup_image_server(port=50001):
    from pmc_camera.utils import log
    log.setup_stream_handler(level=logging.DEBUG)
    ip = '0.0.0.0'
    try:
        pipeline = Pyro4.Proxy('PYRO:pipeline@%s:50000' % ip)
    except Exception as e:
        print "failed to connect to pipeline:", e
        pipeline = None

    server = simple_image_server.SimpleImageServer(pipeline)
    daemon = Pyro4.Daemon(host='0.0.0.0', port=port)
    uri = daemon.register(server, "image")
    print uri
    daemon.requestLoop()


if __name__ == "__main__":
    setup_image_server()

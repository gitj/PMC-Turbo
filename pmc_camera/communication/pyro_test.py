import Pyro4
import time
import select

Pyro4.config.SERVERTYPE = "multiplex"

@Pyro4.expose
class test():
    def setup(self):
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip, port=40000)
        uri = self.daemon.register(self, "test")
        print uri

    def run_pyro_events(self):
        events, _, _ = select.select(self.daemon.sockets, [], [], 0)
        if events:
            self.daemon.events(events)
        else:
            time.sleep(0.001)

    def test(self):
        return 'test'
import collections
import threading
from ..bully_election import Player
import Pyro4

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle']
Pyro4.config.SERVERTYPE = 'multiplexed'
Pyro4.config.COMMTIMEOUT = 0.1

@Pyro4.expose
class DummyPlayer():
    def __init__(self, id, address_book):
        self.address_book = address_book
        self.id = id
        self.player = Player(id=id)
        host,port = address_book[id]
        self.daemon = Pyro4.Daemon(host=host,port=port)
        self.daemon.register(self,'player')
        self.pyro_thread = threading.Thread(target=self.daemon.requestLoop)
        self.pyro_thread.daemon = True
        self.pyro_thread.start()
        self.update_proxies()
    def update_proxies(self):
        proxies = collections.OrderedDict()
        for id,(host,port) in self.address_book.items():
            proxies[id] = Pyro4.Proxy("PYRO:player@%s:%s" % ())
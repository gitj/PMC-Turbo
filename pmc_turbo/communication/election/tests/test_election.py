import collections
import threading
import time
from pmc_turbo.communication.election.bully_election import ConcensusBullyPlayer, SimpleBullyPlayer
import Pyro4
import random

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED = ['pickle']
Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.COMMTIMEOUT = 0.1
import logging
logger = logging.getLogger(__name__)

@Pyro4.expose
class DummyPeer():
    def __init__(self, id, address_book, player_class=SimpleBullyPlayer, main_loop_interval=1):
        self.address_book = address_book
        self.id = id
        self.player = player_class(id=id)
        host,port = address_book[id]
        self.daemon = Pyro4.Daemon(host=host,port=port)
        self.daemon.register(self,'player')
        self.pyro_thread = threading.Thread(target=self.daemon.requestLoop)
        self.pyro_thread.daemon = True
        self.pyro_thread.start()
        self.update_proxies()
        self.player.set_proxies(self.proxies)
        self.main_thread = None
        self.exit=False
        self.ping_value = True
        self.main_loop_interval = main_loop_interval

    def main_loop(self):
        while not self.exit:
            self.player.state_machine()
            if self.main_loop_interval == 'random':
                time.sleep(random.random())
            else:
                time.sleep(self.main_loop_interval)

    def start_player(self):
        if self.main_thread is None:
            self.main_thread = threading.Thread(target=self.main_loop)
            self.main_thread.daemon = True
            self.main_thread.start()
    def update_proxies(self):
        self.proxies = collections.OrderedDict()
        for id,(host,port) in self.address_book.items():
            self.proxies[id] = Pyro4.Proxy("PYRO:player@%s:%s" % (host,port))

    def ping(self):
        return self.ping_value

    def get_leader_id(self):
        return self.player.leader_id

    def notification_of_new_leader(self,leader_id):
        self.player.notification_of_new_leader(leader_id)

def test_bully_election(interval = 0.1):
    import random

    player_class = SimpleBullyPlayer

    num_peers = 4
    address_book = dict([(k,('localhost',57430+k)) for k in range(num_peers)])
    peers = [DummyPeer(k,address_book,player_class=player_class,main_loop_interval=interval) for k in range(num_peers)]
    for peer in peers:
        peer.ping_value = False
    indexes = range(num_peers)
    random.shuffle(indexes)
    indexes = range(num_peers)[::-1]
    for k in indexes:
        peer = peers[k]
        logger.info("starting peer %d" % k)
        time.sleep(random.random()*interval)
        peer.start_player()
        peer.ping_value = True
    logger.info("waiting for a few rounds")
    time.sleep(5*interval)
    for peer in peers:
        logger.info("peer %d has leader %d" % (peer.player.id,peer.player.leader_id))
    logger.info("killing player 0")
    peers[0].ping_value = False
    peers[0].daemon.shutdown()
    time.sleep(5*interval)
    logger.info("ressurecting player 0")
    peers[0].player.leader_id = None
    peers[0].ping_value = True
    time.sleep(5*interval)
    logger.info("shutting down")
    for peer in peers:
        peer.exit = True
        peer.daemon.shutdown()
    time.sleep(3*interval)
    logger.info("done")

if __name__ == "__main__":
    import pmc_turbo.utils.log
    import logging
    logger = pmc_turbo.utils.log.pmc_turbo_logger
    pmc_turbo.utils.log.setup_stream_handler(logging.DEBUG)
    test_bully_election(1)


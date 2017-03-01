import logging
logger = logging.getLogger(__name__)

class Player(object):
    def __init__(self, id):
        self.id = id
        self.proxies = None
        self.leader_id = None
        self.state = "idle"
        logger.debug("Player id %d created" % self.id)
    def set_proxies(self,proxies):
        self.proxies = proxies
        logger.debug("Player id %d setup %d proxies" % (self.id,len(proxies)))


    def notification_of_new_leader(self,leader_id):
        if self.leader_id is not None:
            if self.leader_id == leader_id:
                logger.warning("Player %d got notification of new leader %d but already had that leader assignment" % (self.id,leader_id))
            else:
                logger.warning("Player %d thought the leader was %d but has received notification that leader is %d" % (self.id, self.leader_id, leader_id))
        logger.info("Player %d setting leader id to %d" % (self.id, leader_id))
        self.leader_id = leader_id

    def is_leader_alive(self):
        if self.leader_id is None:
            return False
        return self.is_peer_alive(self.leader_id)

    def is_peer_alive(self,peer_id):
        try:
            return self.proxies[peer_id].ping()
        except Exception: #comm error
            return False

    def get_leader_concensus(self):
        leaders = []
        for proxy_id,proxy in self.proxies.items():
            if proxy_id == self.id:
                continue
            try:
                leader = proxy.get_leader_id()
#                if leader is not None:
                leaders.append(leader)
            except Exception:
                pass
        logger.debug("Player %d with leader %r finds survey results: %r" % (self.id,self.leader_id,leaders))
        if not leaders:
            logger.debug("Player %d no concensus because no response from other players, so I should be leader" % self.id)
            return self.id
#        if None in leaders:
#            logger.debug("Player %d no concensus because at least one player doesn't have  a leader" % self.id)
#            return None
        if set(leaders) == {None}:
            logger.debug("Player %d no one has a leader, so no concensus" % self.id)
            return None
        leaders = [x for x in leaders if x is not None]
        if len(set(leaders)) == 1:
            logger.debug("Player %d found concensus leader value of %d" % (self.id,leaders[0]))
            return leaders[0]
        else:
            logger.debug("Player %d no concensus because players disagree" % self.id)
            return None

class SimpleBullyPlayer(Player):
    def state_machine(self):
        if self.state == "idle":
            if self.is_leader_alive():
                logger.debug("Player id %d idle and leader %d is alive" % (self.id,self.leader_id))
                return
            else:
                logger.info("Player id %d leader has died, going to elect_leader state" % self.id)
                self.leader_id = None
                self.state = "elect_leader"
                return
        elif self.state == "elect_leader":
            for peer_id,proxy in self.proxies.items():
                if peer_id < self.id:
                    if self.is_peer_alive(peer_id):
                        self.state = "wait_for_leader"
                        logger.debug("Player %d found peer with lower id %d, going to wait_for_leader" % (self.id, peer_id))
                        return
                    else:
                        logger.debug("Player %d found peer with lower id %d, but peer is not alive" % (self.id, peer_id))
            ping_result = False
            try:
                ping_result = self.proxies[self.id].ping()
            except Exception:
                logger.debug("Player %d failed to ping self" % self.id)
            if ping_result:
                logger.info("Player %d going to become_leader" % self.id)
                self.state = "become_leader"
            else:
                logger.warning("Player %d is offline for debugging and won't become leader" % self.id)
                self.state = "idle"
            return
        elif self.state == "wait_for_leader":
            if self.leader_id is not None:
                logger.info("Player %d has new leader with id %d" % (self.id, self.leader_id))
                self.state = "idle"
                return
            logger.debug("Player %d Waiting for leader notification" % self.id)
            #time.sleep?
        elif self.state == "become_leader":
            #self.leader_id = self.id #this should be done by the following
            logger.info("Player %d notifying players that I am now leader" % self.id)
            for peer_id,proxy in enumerate(self.proxies.values()):
                try:
                    proxy.notification_of_new_leader(self.id) # check for contention?
                except Exception:
                    logger.warning("Player %d failed to notify player %d that I am now leader because of communication error" % (self.id,peer_id))
            self.state = "idle"


class ConcensusBullyPlayer(Player):
    def state_machine(self):
        if self.state == "idle":
            concensus = self.get_leader_concensus()
            if self.is_leader_alive():
                if concensus is None or concensus != self.leader_id:
                    logger.debug("No concensus on leader, going to elect")
                    self.state = "elect_leader"
                    return
                logger.debug("Player id %d idle and leader %d is alive, and we have concensus" % (self.id,self.leader_id))
                return
            else:
                if concensus is not None and concensus != self.leader_id:
                    self.leader_id = concensus
                    logger.debug("Player id %d leader has died, other peers have consensus, so using leader %d"
                                 % (self.id, self.leader_id))
                    return

                logger.debug("Player id %d leader has died, going to elect_leader" % self.id)
                self.leader_id = None
                self.state = "elect_leader"
                return
        elif self.state == "elect_leader":
            for peer_id,proxy in self.proxies.items():
                if peer_id < self.id:
                    if self.is_peer_alive(peer_id):
                        self.state = "wait_for_leader"
                        logger.debug("Player %d found peer with lower id %d, going to wait_for_leader" % (self.id, peer_id))
                        return
                    else:
                        logger.debug("Player %d found peer with lower id %d, but peer is not alive" % (self.id, peer_id))
            if self.proxies[self.id].ping():
                logger.info("Player %d going to become_leader" % self.id)
                self.state = "become_leader"
            else:
                logger.warning("Player %d is offline for debugging and won't become leader" % self.id)
                self.state = "idle"
            return
        elif self.state == "wait_for_leader":
            if self.leader_id is not None:
                logger.info("Player %d has new leader with id %d" % (self.id, self.leader_id))
                self.state = "idle"
                return
            logger.debug("Player %d Waiting for leader notification" % self.id)
            #time.sleep?
        elif self.state == "become_leader":
            #self.leader_id = self.id #this should be done by the following
            logger.info("Player %d notifying players that I am now leader" % self.id)
            for proxy in self.proxies.values():
                proxy.notification_of_new_leader(self.id) # check for contention?
            self.state = "idle"


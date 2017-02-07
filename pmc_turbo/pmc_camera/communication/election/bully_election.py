
class Player(object):
    def __init__(self, id):
        self.id = id
        self.proxies = None
        self.leader_id = None
        self.state = "elect_leader"
    def set_proxies(self,proxies):
        self.proxies = proxies
    def state_machine(self):
        if self.state == "idle":
            if self.is_leader_alive():
                return
            else:
                self.leader_id = None
                self.state = "elect_leader"
                return
        elif self.state == "elect_leader":
            for peer_id,proxy in self.proxies.items():
                if peer_id < self.id:
                    if self.is_peer_alive(peer_id):
                        self.state = "wait_for_leader"
                        return
            self.state = "become_leader"
            return
        elif self.state == "wait_for_leader":
            if self.leader_id is not None:
                self.state = "idle"
                return
            #time.sleep?
        elif self.state == "become_leader":
            #self.leader_id = self.id #this should be done by the following
            for proxy in self.proxies.values():
                proxy.notification_of_new_leader(self.id) # check for contention?
    def notification_of_new_leader(self,leader_id):
        if self.leader_id is not None:
            print "New leader,",leader_id," has assumed role, but I thought the leader was",self.leader_id
        self.leader_id = leader_id
    def is_leader_alive(self):
        if self.leader_id is None:
            return False
        return self.is_peer_alive(self.leader_id)

    def is_peer_alive(self,peer_id):
        try:
            self.proxies[peer_id].ping()
            return True
        except Exception: #comm error
            return False

    def find_leader(self):
        for peer_id,proxy in self.proxies.items():
            if peer_id < self.id:
                if self.is_peer_alive(peer_id):
                    self.wait_for_leader()
        self.become_leader()


import zmq
import json
import time

class Camera_Controller():
    def __init__(self, base_port, cam_id):
        self.base_port = base_port
        self.cam_id = cam_id
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://*:%s" % str(self.base_port+self.cam_id))
        self.other_camera_sockets = []
        self.master = None
        self.kvdb = dict(value=4.6)
        self.command_dict = dict(give_kvdb=self.send_kvdb)

    def connect_to_other_cameras(self, num_cameras):
        for i in range(num_cameras):
            if i != self.cam_id:
                new_socket = self.context.socket(zmq.PAIR)
                new_socket.connect("tcp://localhost:%s" % (self.base_port+i))
                self.other_camera_sockets.append(new_socket)
            # Switch to a list of ports that will be assigned to camera.

    def send_kvdb(self):
        self.socket.send_json(self.kvdb)
        #self.socket.send('test')

    def determine_master(self):
        # Look for Camera_Controller with higher number, if none exists, I am the master.
        return

    def listen_for_command(self):
        while True:
            if self.socket.poll(timeout=0):
                command = self.socket.recv()
                if command in self.command_dict:
                    self.command_dict[command]()
            time.sleep(0.1)


    def get_other_camera_info(self):
        for socket in self.other_camera_sockets:
            kvdb = self.request_kvdb(socket)

    def send_command(self, command, other_camera_socket):
        other_camera_socket.send(command)

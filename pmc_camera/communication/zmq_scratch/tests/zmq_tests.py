import cam_cpu


def command_response_test():
    cam0 = cam_cpu.Camera_Controller(5556, 0)
    cam1 = cam_cpu.Camera_Controller(5556, 1)
    cam0.connect_to_other_cameras(2)
    cam0.send_command('give_kvdb', cam0.other_camera_sockets[0])
    command = cam1.socket.recv()
    print command
    cam1.command_dict[command]()
    print cam0.other_camera_sockets[0].recv()

if __name__ == "__main__":
    command_response_test()

import socket

def get_camera_id():
    hostname = socket.gethostname()
    if hostname.startswith('pmc-camera-'):
        try:
            return int(hostname[-1])
        except Exception:
            pass
    #raise RuntimeError("Could not determine camera id from hostname %s" % hostname)
    return 255
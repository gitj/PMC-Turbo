import cobs.cobs

def encode_data(data):
    a = cobs.cobs.encode(data)
    b = a.replace('\x10', '\x00')
    c = cobs.cobs.encode(b)
    d = c.replace('\x10', '\x00')
    return d

def decode_data(data):
    e = data.replace('\x00', '\x10')
    f = cobs.cobs.decode(e)
    g = f.replace('\x00', '\x10')
    h = cobs.cobs.decode(g)
    return h
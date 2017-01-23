import os

BLOCK_SIZE = 1024


def read_last_line(file_):
    buffer = ''
    with open(file_, 'r') as f:
        f.seek(0, os.SEEK_END)
        block_end_byte = f.tell()
        block_number = -1
        while True:
            if (block_end_byte - BLOCK_SIZE) > 0:
                f.seek(block_number * BLOCK_SIZE, os.SEEK_END)
                buffer = f.read(BLOCK_SIZE) + buffer
            else:
                # File is too small to include full block
                f.seek(0, 0)
                buffer += f.read(block_end_byte)
                return buffer.split('\n')[-2]
                # We don't really have an option here to do anything else.
            idx = buffer.find('\n')
            if idx == -1:
                raise ValueError('No newline found at end of file. Buffer is %r' % buffer)
            if idx == len(buffer) - 1:
                block_number -= 1
                continue
            else:
                # Last entry of split should be empty, next is the actual last line.
                return buffer.split('\n')[-2]

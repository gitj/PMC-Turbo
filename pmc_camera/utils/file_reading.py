import os

BLOCK_SIZE = 50


def read_last_line(file_):
    buffer = ''
    with open(file_, 'r') as f:
        f.seek(0, os.SEEK_END)
        block_end_byte = f.tell()
        block_number = -1

        while True:
            if (block_end_byte - BLOCK_SIZE) > 0:
                f.seek(block_number * BLOCK_SIZE, os.SEEK_END)
                buffer += f.read(BLOCK_SIZE)
            else:
                # File is too small to include full block
                f.seek(0, 0)
                buffer += f.read(block_end_byte)
                return buffer.split('\n')[-2]
                # We don't really have an option here to do anything else.
            lines = buffer.split('\n')
            if len(lines) >= 3:
                # We need at least 3 to make sure we got a complete line
                # The last entry is whatever follows the terminating \n (this will usually be '')
                # The second to last entry is a complete line
                # The third to last entry is whatever preceeds the complete line.
                # We need to check this to make sure we got a complete line.
                if len(lines[-2]) == 0:
                    raise ValueError('Line length is zero, something went wrong.')
                return lines[-2]

import subprocess
import random

def get_random_process():
    output = subprocess.check_output("ps -e -o pid= -o command=", shell=True)
    lines = output.splitlines()
    line = random.sample(lines,1)[0]
    print line
    return line

if __name__ == "__main__":
    get_random_process()
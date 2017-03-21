import sys
import os

ip = sys.argv[1]
identity = "-i /home/pmc/.ssh/id_rsa_pmc"

def run_command(command):
    print "+ " + command
    os.system(command)
#run_command('scp %s /home/pmc/pmc-turbo/scripts/installation/etc/sudoers root@%s:/etc/sudoers' % (identity,ip))
run_command('ssh %s %s "git clone https://github.com/PolarMesosphericClouds/PMC-Turbo.git ~/pmc-turbo"' % (identity, ip))
run_command('ssh %s %s "cd pmc-turbo; git pull"' % (identity, ip))
run_command('ssh -t %s %s "su -c \\\"cp /home/pmc/pmc-turbo/scripts/installation/etc/sudoers /etc/sudoers\\\""' % (identity, ip))
run_command('ssh %s %s "sudo cp /home/pmc/pmc-turbo/scripts/installation/etc/pmc-turbo-hosts /etc/hosts"' % (identity, ip))

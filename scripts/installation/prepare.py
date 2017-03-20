import sys
import os

ip = sys.argv[1]
identity = "-i /home/pmc/.ssh/id_rsa_pmc"
#os.system('scp %s /home/pmc/pmc-turbo/scripts/installation/etc/sudoers root@%s:/etc/sudoers' % (identity,ip))
os.system('ssh %s %s "git clone https://github.com/PolarMesosphericClouds/PMC-Turbo.git ~/pmc-turbo"' % (identity, ip))
os.system('ssh %s %s "cd pmc-turbo; git pull"' % (identity, ip))
os.system('ssh -t %s %s "su -c \"cp /home/pmc/pmc-turbo/scripts/installation/etc/sudoers /etc/sudoers\""' % (identity, ip))
os.system('ssh %s %s "sudo cp /home/pmc/pmc-turbo/scripts/installation/etc/pmc-turbo-hosts /etc/hosts"' % (identity, ip))

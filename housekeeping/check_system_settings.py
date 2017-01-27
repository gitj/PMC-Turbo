"""
This file is intended to be run manually with nosetests
"""
from subprocess import check_output

def test_sudo_no_password():
    try:
        result = check_output('sudo -n -l | grep NOPASSWD',shell=True)
        if result.find('NOPASSWD') >=0:
            return
    except Exception:
        pass
    assert False


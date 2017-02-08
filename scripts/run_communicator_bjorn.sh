#!/bin/bash
if ! [ -f /home/pmc/pmchome/mounted ];
    then /home/pmc/mount_pmchome.sh;
fi
export PATH=/home/pmc/miniconda2/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmchome/pmc-turbo
exec python /home/pmc/pmchome/pmc-turbo/pmc_turbo/pmc_camera/utils/run_communicator.py
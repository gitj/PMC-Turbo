#!/bin/bash
export PATH=/home/pmc/miniconda/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmchome/pmc-turbo-devel
exec python /home/pmc/pmchome/pmc-turbo-devel/scripts/python/run_communicator.py
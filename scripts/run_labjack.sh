#!/bin/bash
export PATH=/home/pmc/miniconda/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmc-turbo
python /home/pmc/pmc-turbo/pmc_turbo/housekeeping/labjack.py
#!/bin/bash
export PATH=/home/pmc/miniconda2/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmc-turbo
python /home/pmc/pmc-turbo/housekeeping/labjack.py
#!/bin/bash
export PATH=/home/pmc/miniconda2/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmc-turbo
exec python /home/pmc/pmc-turbo/scripts/run_controller.py
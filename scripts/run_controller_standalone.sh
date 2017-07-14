#!/bin/bash
export PATH=/home/pmc/miniconda/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmc-turbo
exec python /home/pmc/pmc-turbo/scripts/python/run_controller.py --config_file=standalone_balloon.py
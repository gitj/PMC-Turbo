#!/bin/bash
source activate pmc
export PYTHONPATH=/home/pmc/pmc-turbo
export LD_LIBRARY_PATH=/home/pmc/Vimba_2_0/VimbaCPP/DynamicLib/x86_64bit
python /home/pmc/pmc-turbo/pmc_camera/utils/run_pipeline.py
#!/bin/bash
export PATH=/home/pmc/miniconda2/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmchome/pmc-turbo-devel
export GENICAM_GENTL64_PATH=$GENICAM_GENTL64_PATH:"/home/pmc/Vimba_2_0/VimbaGigETL/CTI/x86_64bit"
export LD_LIBRARY_PATH=/home/pmc/Vimba_2_0/VimbaCPP/DynamicLib/x86_64bit
exec python /home/pmc/pmchome/pmc-turbo-devel/pmc_camera/utils/run_pipeline.py
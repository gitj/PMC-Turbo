#!/bin/bash
if ! [ -f /home/pmc/pmchome/mounted ];
    then /home/pmc/mount_pmchome.sh;
fi
export PATH=/home/pmc/miniconda2/bin:$PATH
source activate pmc
export PYTHONPATH=/home/pmc/pmchome/pmc-turbo
export GENICAM_GENTL64_PATH=$GENICAM_GENTL64_PATH:"/home/pmc/Vimba_2_0/VimbaGigETL/CTI/x86_64bit"
export LD_LIBRARY_PATH=/home/pmc/Vimba_2_0/VimbaCPP/DynamicLib/x86_64bit
exec python /home/pmc/pmchome/pmc-turbo/pmc_turbo/pmc_camera/utils/run_controller.py
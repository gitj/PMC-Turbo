#!/bin/bash
pushd $HOME
curl -L -O https://cdn.alliedvision.com/fileadmin/content/software/software/Vimba/Vimba_v2.0_Linux.tgz
tar -xf Vimba_v2.0_Linux.tgz
export VIMBA_ROOT="$PWD/Vimba_2_0"
popd
wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh -O miniconda.sh;
bash miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"
hash -r
conda update -q conda
  # Useful for debugging any issues with conda
conda info -a
pushd pmc-turbo
conda env create -q -n pmc -f environment.yml
popd
source activate pmc
pushd $HOME
git clone --depth=10 --branch=master https://github.com/labjack/LabJackPython.git
cd LabJackPython
pip install .
popd
cd $HOME
pushd pmc_turbo/camera/pycamera/_pyvimba
make
popd
cd pmc-turbo
nosetests -v -s --with-coverage --cover-erase --cover-xml --cover-inclusive --cover-package=pmc_turbo

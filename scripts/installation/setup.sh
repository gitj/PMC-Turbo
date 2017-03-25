#!/bin/bash
set -x
#PMC_TURBO=$HOME/pmchome/pmc-turbo-devel
PMC_TURBO=$HOME/pmc-turbo
sudo cp etc/interfaces.d/eth1 /etc/network/interfaces.d/
sudo /etc/init.d/networking restart
mkdir $HOME/Downloads
pushd $HOME/Downloads/
git clone https://github.com/ptpd/ptpd.git
cd ptpd
autoreconf -vi
./configure
make -j8
sudo make install
popd
pushd $HOME
curl -L -O https://cdn.alliedvision.com/fileadmin/content/software/software/Vimba/Vimba_v2.0_Linux.tgz
tar -xf Vimba_v2.0_Linux.tgz
export VIMBA_ROOT="$PWD/Vimba_2_0"
sudo $VIMBA_ROOT/VimbaGigETL/Install.sh
echo $VIMBA_ROOT/VimbaCPP/DynamicLib/x86_64bit | sudo tee /etc/ld.so.conf.d/vimba.conf
sudo ldconfig
popd
pushd $HOME/Downloads/
wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh -O miniconda.sh;
bash miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$VIMBA_ROOT/Tools/Viewer/Bin/x86_64bit:$PATH"

echo "export PATH=/home/pmc/miniconda/bin:$VIMBA_ROOT/Tools/Viewer/Bin/x86_64bit:\$PATH" >> ~/.bashrc
hash -r
conda update -y conda
  # Useful for debugging any issues with conda
conda info -a
pushd $PMC_TURBO
conda env create -n pmc -f environment.yml
popd
source activate pmc
sudo apt-get install libusb-1.0-0-dev  #this should be preseeded, but just in case
pushd $HOME/Downloads/
git clone git://github.com/labjack/exodriver.git
cd exodriver
sudo ./install.sh
cd ..
git clone --depth=10 --branch=master https://github.com/labjack/LabJackPython.git
cd LabJackPython
pip install .
popd
# this test wont work until after reboot:
#python -c "import u3; lj = u3.U3()"
pushd $PMC_TURBO/pmc_turbo/camera/pycamera/_pyvimba
make
popd
echo "export PYTHONPATH=$PMC_TURBO" >> $HOME/.bashrc
cd $PMC_TURBO
nosetests -v -s

sudo cp $PMC_TURBO/scripts/installation/etc/fuse.conf /etc/
sudo cp $PMC_TURBO/scripts/installation/etc/collectd.conf /etc/collectd/
sudo cp $PMC_TURBO/scripts/installation/etc/hddtemp /etc/default/

mkdir $HOME/pmchome
sudo cp -r $PMC_TURBO/scripts/installation/etc/supervisor /etc/
sudo supervisorctl reread
sudo supervisorctl update
sleep 1
sudo supervisorctl status
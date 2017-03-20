#!/bin/bash
sudo cp etc/interfaces.d/eth1 /etc/network/interfaces.d/
sudo /etc/init.d/networking restart
pushd $HOME/Downloads/
git clone https://github.com/ptpd/ptpd.git
cd ptpd
autoreconf -vi
./configure
make -j8
sudo make install
popd
sudo cp -r etc/supervisor /etc/
sudo supervisorctl reread
sudo supervisorctl update
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
export PATH="$HOME/miniconda/bin:$PATH"
echo "export PATH=/home/pmc/miniconda/bin:\$PATH" >> ~/.bashrc
hash -r
conda update -q conda
  # Useful for debugging any issues with conda
conda info -a
pushd $HOME/pmc-turbo
conda env create -q -n pmc -f environment.yml
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
python -c "import u3; u3 = U3.U3()"
pushd $HOME/pmc_turbo/camera/pycamera/_pyvimba
make
popd
echo $HOME/pmc-turbo >> $HOME/.bashrc
cd $HOME/pmc-turbo
nosetests -v -s --with-coverage --cover-erase --cover-xml --cover-inclusive --cover-package=pmc_turbo

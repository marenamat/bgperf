#!/bin/bash
#git clone https://github.com/jopietsch/bgperf.git
sudo apt update
sudo apt upgrade --yes
sudo apt install docker.io --yes
sudo apt install python3-pip --yes
sudo apt install sysstat --yes
sudo apt install emacs-nox --yes
sudo usermod -aG docker ubuntu

cd bgperf
pip3 install -r pip-requirements.txt
wget -q http://archive.routeviews.org/bgpdata/2021.08/RIBS/rib.20210801.0000.bz2 && bzip2 rib.20210801.0000.bz2
sudo /sbin/shutdown now -r
# the user group permissions need to be applied, so easiest to log out
#python3 bgperf.py prepare && python3 bgperf.py update frr_c && python3 bgperf.py update bgpdump2

## HOST Machine operator setup manual

These are instructions on how to setup your own machine to run the software we use in the GUI application. 
**If you're looking for the GUI Operator's manual, that is a separate file.**

#### Windows:
- [x] Install [Python 3.7](https://www.python.org/downloads/windows/)
- [x] Install [Git](https://git-scm.com/downloads) 
- [x] Check for pip installation `python3 -m pip --version` 
- [x] Install pip from [here](https://pip.pypa.io/en/stable/installing/) if not installed 
- [x] Install dependency libraries for the GUI
- [x] `pip install grpcio==1.38.0 opencv-python==4.5.1.48 google-api-python-client==2.8.0 pillow==8.2.0 pygame==2.0.1`

#### Linux:
- [x] `sudo apt-get update`
- [x] `sudo apt-get install git python3-dev`
- [x] In addition to installing python dependencies below, install contrib **AFTER OPENCV**: ``
- [x] Check for pip installation `sudo python3 -m pip --version`
- [x] Install pip if not installed: `sudo apt-get install python3-pip` 
- [x] Install dependency libraries for the GUI
- [x] `sudo pip install grpcio==1.38.0 opencv-python==4.5.1.48 opencv-contrib-python==4.5.2.54 google-api-python-client==2.8.0 pillow==8.2.0 pygame==2.0.1`

#### Git
- [x] `git clone <this repo>`
- [x] `cd <this repo>`
- [x] `git init`
- [x] `git fetch`
- [x] `git checkout <whatever branch GUI is on>` 

#### Running on Windows:
- [x] `tools/scripts/setup_win.bat`
- [x] `python3 gui/main.py`

#### Running on Linux:
- [x] `. setup.sh`
- [x] `python3 gui/main.py`

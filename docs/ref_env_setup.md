# Main Environment setup document, please read!

## Environment Setup - Raspberry pi

#### Required Hardware:
###### Raspberry Pi 4 
###### USB Type C Power Cable (Ideally > 2A) 
###### SD Card (Ideally > 16GB) 
###### Ethernet Cable with Internet

#### Optional Hardware (if you don't set the IP before writing the image): 
###### Micro HDMI Cable or Micro HDMI Adapter
###### Display Monitor for Terminal
###### Keyboard

#### OS: 
[Ubuntu Server 20.04.2 64 Bit for ARM](https://ubuntu.com/download/raspberry-pi/thank-you?version=20.04.2&architecture=server-arm64+raspi)

#### Software install and usage

##### OS and Python dependencies
- [x] Plug in SD card, Ethernet, then power the Pi. Keyboard and HDMI optional.
- [x] Login on default username/password `ubuntu/ubuntu` and change password.
- [x] `ip address` Note IP address obtained via DHCP for SSH. Monitor and Keyboard no longer necessary.
- [x] On another machine, open an SSH session. SSH should be enabled on the Pi by default.
- [x] `sudo apt-get update`
- [x] `sudo reboot`
- [x] `sudo apt-get install git python3-dev`
- [x] `sudo apt-get install python3-pip`
- [x] `sudo pip3 install grpcio`
- [x] `sudo pip3 install google-api-python-client`
- [x] `sudo pip3 install opencv-python==4.5.1.48`
- [x] `sudo pip3 install opencv-contrib-python==4.5.2.54`

##### Docker
From [here](https://docs.docker.com/engine/install/ubuntu/)
- [x] `sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release`
- [x] `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg`
- [x] `echo \
  "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`
- [x] `sudo apt-get update` Yes, you have to run apt-get here even though it was run earlier.
- [x] `sudo apt-get install docker-ce docker-ce-cli containerd.io`
- [x] `sudo pip3 install docker`

##### Git and container setup
- [x] `git clone https://github.com/DOCgould/MechatronicsRobosub2021` 
- [x] `git init`
- [x] `git checkout <relevant branch>`
- [x] `sudo -i`
- [x] `cd <Mechatronics directory>`
- [x] `. setup.sh`
- [x] `cd tools/scripts`
- [x] `. build_<relevant_container>.sh` Run whatever build scripts you want but make sure it's done from this directory
- [x] If building additional containers, `cd tools/scripts` and run additional build scripts.

##### Testing containers with GUI
- [x] `cd <repo_directory>`
- [x] `python3 src/Intelligence/all_systems_demo.py`

##### Starting Containers
- [x] `. <repo_directory>/tools/scripts/start_all_containers.sh`

##### Killing Containers
- [x] `. <repo_directory>/tools/scripts/kill_all_containers.sh`


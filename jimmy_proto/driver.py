import cv2
from inference_dir.gate_detector import GateDetector
import docker
CLIENT = docker.from_env()
from new import SimpleDevice
import sys, time
import os
import client as client


def DestroyAllContainers():
    containers_list = CLIENT.containers.list(all=True)
    for cont in containers_list:
        cont.remove(force=True)
	
	
DestroyAllContainers()
print("")
print("Initializing the state machine ...")
print("-" * 70)
dev = SimpleDevice()
print("System Check is Good ...")
print("Moving on to Normal Operation")
# ----------------------------------------
dev.on_event("Normal_Operation")  # ---> Unlocked STae
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
# ----------------------------------------
print("Doing System Checkup ...")
dev.on_event("Caution_Operation") #---> Caution State
print("Current State of the State Machine\n")
print(dev.state, "\n")
# ----------------------------------------
print("Returning to normal operations....")
dev.on_event("Normal_Operation")  # ---> Unlocked State
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
# ----------------------------------------
print("Doing System Checkup ...")
dev.on_event("Caution_Operation") #---> Caution State
print("Current State of the State Machine\n")
print(dev.state, "\n")
# ----------------------------------------
print("Emulating an Error Occurrring ...")
dev.on_event("Error_Operation")  # ---> Locked
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
# ----------------------------------------
print("System Recovered ...")
print("Doing System Checkup ...")
dev.on_event("Caution_Operation")
print("Current State of the State Machine\n")
print(dev.state, "\n")
# simple_device.py
time.sleep(5)
print("--" * 70)
print("Simulation Complete.")
print("Destroying All Containers ")
DestroyAllContainers()

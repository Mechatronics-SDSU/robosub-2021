#!/usr/bin/env python3
import docker
import time

WAIT_TIME = 5
host = docker.from_env()
fullsystem_img = host.images.build(path="./",
                         tag="server",
                         rm=True)

print("-"*35, "FINISHED MAIN BUILD", "-"*35)

vols={"/sock":{"bind": "/SOCKETS", "mode": 'rw'},
"/home/christian/Workspace/GITS/MechatronicsRobosub2021/src/base/test2/proto":{"bind": "/src/proto", 'mode': "rw"}}


print("Starting Server...")

host.containers.run(image="server", 
              auto_remove=True,
              volumes=vols,
              detach=True,
              privileged=True)

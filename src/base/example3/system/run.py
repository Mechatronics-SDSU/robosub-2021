#!/usr/bin/env python3
import docker
import time

WAIT_TIME = 5
host = docker.from_env()
fullsystem_img = host.images.build(path="./",
                         tag="example-buld",
                         rm=True)

print("-"*35, "FINISHED MAIN BUILD", "-"*35)

vols={"/home/christian/Workspace/GITS/MechatronicsRobosub2021/src/base/test/SOCKETS":{"bind": "/SOCKETS", "mode": 'rw'},
"/home/christian/Workspace/GITS/MechatronicsRobosub2021/src/base/test/gen":{"bind": "/gen", 'mode': "rw"}}


print("Starting Server...")

host.containers.run(image="example-buld", 
              command="server",
              auto_remove=True,
              volumes=vols,
              detach=True)

start = time.time()

while(time.time() - start < WAIT_TIME):
    print("Starting in ...", time.time() - start, end="\r")

host.containers.run(image="example-buld", 
              command="client",
              auto_remove=True,
              volumes=vols,
              detach=True)

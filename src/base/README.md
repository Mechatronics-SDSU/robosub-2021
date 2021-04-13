# Baseline Docker Container

> The container below all containers
> This container is the container all builds come from

### What is in it?
For now, ubuntu-base, and eventually a application that will make sending messages easier

### How do I use it?
you'll build it, the same way we build other containers, using the pyhton-api for docker
see the example by running the following

```
~$ ./run.py
```
then open another terminal and run - this will show you what the container is doing
```
docker ps -a
```
Once both the "server and client" are running
run the following
```
~$ python3 fullsystem.py server
```
This should print a live stream of the time from inside the client to the server - or - from the "sending container" to the "listening containers"
because both containers are listending to the same socket, we're sucessfully sending the packet to two different destinations

# Disclaimer - This is not done yet!
just putting the skeleton out

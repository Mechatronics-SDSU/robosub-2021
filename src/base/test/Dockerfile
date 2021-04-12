FROM ubuntu:20.04

ADD fullsystem.py /
ADD gen /

RUN apt-get update && apt-get install -y python3 python3-pip
RUN python3 -m pip install --upgrade protobuf

VOLUME /SOCKETS

ENTRYPOINT ["/fullsystem.py"]

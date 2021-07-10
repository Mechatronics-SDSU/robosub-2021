FROM ubuntu

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update 
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN pip3 install grpcio
RUN pip3 install protobuf
RUN apt-get install -y protobuf-compiler
RUN apt-get update && apt-get install -y python3-opencv
RUN pip3 install opencv-python
RUN pip3 install opencv-contrib-python
RUN apt-get install tmux -y

MAINTAINER <jimmymusser@gmail.com>

WORKDIR /home/protobufs/

COPY . .

#ENTRYPOINT ["python3"]

#CMD ["run_data.py"]

CMD ["/bin/bash"]

FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update 
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN pip3 install grpcio
RUN pip3 install protobuf
RUN apt-get install -y protobuf-compiler
RUN apt-get update && apt-get install -y python3-opencv
RUN pip3 install opencv-python==4.3.0.36
RUN pip3 install opencv-contrib-python==4.3.0.36
RUN apt-get install tmux -y

ENV PYTHONPATH="${PYTHONPATH}:/"

EXPOSE 50051

ADD ./ ./
WORKDIR .

COPY . .

#ENTRYPOINT ["python3"]

CMD ["python3","/src/Intelligence/server.py"]


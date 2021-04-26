FROM jjanzic/docker-python3-opencv

WORKDIR /server

RUN python3 -m pip install grpcio grpcio-tools numpy

COPY . /server/.

CMD [ "python3", "server.py"]

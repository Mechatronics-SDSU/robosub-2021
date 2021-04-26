FROM jjanzic/docker-python3-opencv

WORKDIR /src/server

RUN python3 -m pip install grpcio grpcio-tools numpy

COPY gamma_testing .
COPY protos /src/.

CMD [ "python3", "server.py"]

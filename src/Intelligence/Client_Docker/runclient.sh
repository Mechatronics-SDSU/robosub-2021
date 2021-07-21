#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp $(pwd)/src/Intelligence/Client_Docker/Dockerfile $(pwd)/Dockerfile

docker build . -t client_container
#del Dockerfile

docker run -dit --name client --network sc-arch --publish 65431:65431 --publish 50052:50052 client_container 

docker container attach client

PING server_container

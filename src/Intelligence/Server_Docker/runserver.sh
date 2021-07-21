#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp $(pwd)/src/Intelligence/Server_Docker/Dockerfile $(pwd)/Dockerfile

docker network create sc-arch

docker build . -t server_container
#del Dockerfile


docker run -dit --name server --network sc-arch --publish 65432:65432 --publish 50051:50051 server_container 

docker container attach server


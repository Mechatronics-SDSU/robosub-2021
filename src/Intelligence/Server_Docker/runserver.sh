#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp "$(pwd)/src/Intelligence/Server_Docker/Dockerfile" "$(pwd)/Dockerfile"


docker build . -t server_container
#del Dockerfile

docker network create sc-arch

docker run -dit --name server --publish 65432:65432 --network=host server_container 

docker container attach server

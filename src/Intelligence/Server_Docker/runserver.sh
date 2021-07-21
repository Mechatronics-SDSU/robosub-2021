#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp "$(pwd)/src/Intelligence/Server_Docker/Dockerfile" "$(pwd)/Dockerfile"


docker build . -t server_container
#del Dockerfile


docker run -dit --name server --publish 65431:65431 --publish 50052:50052 server_container 

docker container attach server


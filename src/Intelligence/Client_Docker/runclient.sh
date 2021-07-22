#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp "$(pwd)/src/Intelligence/Client_Docker/Dockerfile" "$(pwd)/Dockerfile"

docker build . -t client_container
#del Dockerfile

docker run -dit --name client --publish 50051:50051 --network=host client_container 

docker container attach client



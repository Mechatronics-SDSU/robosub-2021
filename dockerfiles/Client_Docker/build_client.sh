#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cp "$(pwd)/dockerfiles/Client_Docker/Dockerfile" "$(pwd)/Dockerfile"

docker build . -t client_container
docker run -dit --name client --publish 50051:50051 --network=host client_container
docker container attach client

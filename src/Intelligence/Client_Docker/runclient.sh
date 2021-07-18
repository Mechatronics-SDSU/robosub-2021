#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..
cd ..

cp $(pwd)/src/Intelligence/Client_Docker/Dockerfile $(pwd)/Dockerfile

docker build . -t client_container
#del Dockerfile

docker run --name client --publish 65432:65432 --publish 50051:50051 client_container

#!/bin/sh
echo "Setting up Server Container"

cd ..
cd ..

cp $(pwd)/src/Intelligence/Dockerfile $(pwd)/Dockerfile

docker build . -t server_container
#del Dockerfile

docker run --name server --publish 65432:65432 --publish 50051:50051 server_container

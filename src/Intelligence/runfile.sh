#!/bin/sh
echo "Setting up Logging Container"
cd ..
cd ..
cp $(pwd)/src/Intelligence/Dockerfile $(pwd)/Dockerfile

docker build . -t server_container
#del Dockerfile

docker run --name server --publish 50002:50002 server_container

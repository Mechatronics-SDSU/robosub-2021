#!/bin/sh
echo "Setting up Logging Container"
cd ..
cd ..
cp $(pwd)/dockerfiles/Logging/Dockerfile $(pwd)/Dockerfile
cp $(pwd)/dockerfiles/Logging/requirements.txt $(pwd)/requirements.txt
docker build . -t logging_container
rm Dockerfile
rm requirements.txt
echo "Setup Complete."
docker run --name int_logging --publish 50002:50002 logging_container

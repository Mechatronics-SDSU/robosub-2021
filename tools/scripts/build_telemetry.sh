#!/bin/sh
echo "Setting up Telemetry Container"
cd ..
cd ..
cp "$(pwd)/dockerfiles/Telemetry/Dockerfile" "$(pwd)/Dockerfile"
cp "$(pwd)/dockerfiles/Telemetry/requirements.txt" "$(pwd)/requirements.txt"
docker build . -t telemetry_container
rm Dockerfile
rm requirements.txt
echo "Setup Complete."
docker run --name ctrl_telemetry --publish 50003:50003 telemetry_container

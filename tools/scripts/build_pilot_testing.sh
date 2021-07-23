#!/bin/sh
echo "Setting up Pilot Container"
cd ..
cd ..
cp "$(pwd)/dockerfiles/Pilot_Testing/Dockerfile" "$(pwd)/Dockerfile"
cp "$(pwd)/dockerfiles/Pilot_Testing/requirements.txt" "$(pwd)/requirements.txt"
docker build . -t pilot_container
rm Dockerfile
rm requirements.txt
echo "Setup Complete."
docker run --name ctrl_pilot --publish 50004:50004 pilot_container

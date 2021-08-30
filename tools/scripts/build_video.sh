#!/bin/sh
echo "Setting up Video Container"
cd ..
cd ..
cp "$(pwd)/dockerfiles/Video/Dockerfile" "$(pwd)/Dockerfile"
cp "$(pwd)/dockerfiles/Video/requirements.txt" "$(pwd)/requirements.txt"
docker build . -t video_container
rm Dockerfile
rm requirements.txt
echo "Setup Complete."
docker run --name inf_video --device /dev/video0:/dev/video0  --publish 50001:50001 video_container


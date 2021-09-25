#!/bin/sh
echo "Setting up Pilot Container"
cd ..
cd ..
dev="$( cat "$(pwd)"/dockerfiles/Pilot_Complete/maestro_device.txt )"
cp "$(pwd)/dockerfiles/Pilot_Complete/Dockerfile" "$(pwd)/Dockerfile"
cp "$(pwd)/dockerfiles/Pilot_Complete/requirements.txt" "$(pwd)/requirements.txt"
echo "CMD [ \"python3\", \"/src/Control/pilot_server.py\", \"" "$dev" "\" ]" >> Dockerfile
#echo "$dev" >> Dockerfile
#echo "\" ]" >> Dockerfile
docker build . -t pilot_container
rm Dockerfile
rm requirements.txt
echo "Setup Complete."
docker run --name ctrl_pilot --device="$dev":"$dev" --publish 50004:50004 pilot_container

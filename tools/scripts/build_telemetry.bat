@ECHO ON
cd ..
cd ..
copy "%cd%\dockerfiles\Telemetry\Dockerfile" "%cd%\Dockerfile"
copy "%cd%\dockerfiles\Telemetry\requirements.txt" "%cd%\requirements.txt"
docker build . -t telemetry_container
del Dockerfile
del requirements.txt
docker run --name ctrl_telemetry --network all_systems_demo --publish 50003:50003 telemetry_container

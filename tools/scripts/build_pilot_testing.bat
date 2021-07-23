@ECHO ON
cd ..
cd ..
copy "%cd%\dockerfiles\Pilot_Testing\Dockerfile" "%cd%\Dockerfile"
copy "%cd%\dockerfiles\Pilot_Testing\requirements.txt" "%cd%\requirements.txt"
docker build . -t pilot_container
del Dockerfile
del requirements.txt
docker run --name ctrl_pilot --publish 50004:50004 pilot_container

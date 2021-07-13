@ECHO ON
cd ..
cd ..
copy "%cd%\dockerfiles\Pilot\Dockerfile" "%cd%\Dockerfile"
copy "%cd%\dockerfiles\Pilot\requirements.txt" "%cd%\requirements.txt"
docker build . -t pilot_container
del Dockerfile
del requirements.txt
docker run -p 50004:50004 pilot_container
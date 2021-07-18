@ECHO ON
cd ..
cd ..
copy "%cd%\dockerfiles\Logging\Dockerfile" "%cd%\Dockerfile"
copy "%cd%\dockerfiles\Logging\requirements.txt" "%cd%\requirements.txt"
docker build . -t logging_container
del Dockerfile
del requirements.txt
docker run --name int_logging --publish 50002:50002 logging_container
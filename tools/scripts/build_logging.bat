@ECHO ON
cd ..
cd ..
copy "%cd%\dockerfiles\Logging\Dockerfile" "%cd%\Dockerfile"
copy "%cd%\dockerfiles\Logging\requirements.txt" "%cd%\requirements.txt"
docker build . -t logging_container
del Dockerfile
del requirements.txt
docker run -p 50002:50002 logging_container
::docker run --network host logging_container
docker container rm -f $(docker ps -a | awk '{print $1}')

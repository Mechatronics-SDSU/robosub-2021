CUR_USER = $USER
docker build -t server . 
echo "[DEBUG] Docker Container Built ..."
sleep .2
echo "[DEBUG] Starting the Server ..."
sleep .2
docker run --rm -itd -v /sock:/sock:rw --privileged --env=DISPLAY=:0 --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw --device=/dev/video0:/dev/video0:rw --user "$(id -u):$(id -g)" server
echo 'Open client in new terminal!'
echo "Starting docker 'watch session'"
watch docker ps -a

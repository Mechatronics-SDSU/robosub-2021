echo "Starting server ..."
$(docker run -i --rm -v /home/christian/Workspace/examples_workspace/docker_protobuf/Python/SOCKETS:/SOCKETS -v $PWD/gen:/gen example-build server)&
echo "Starting client ..."
docker run --rm -v /home/christian/Workspace/examples_workspace/docker_protobuf/Python/SOCKETS:/SOCKETS -v $PWD/gen:/gen example-build client

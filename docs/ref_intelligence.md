<h2> To start data stream from client to server <h2> 

> run the runserver.sh in MechatronicsRobosub2021/src/Intelligence/Server_Docker/

> run the runclient.sh in MechatronicsRobosub2021/src/Intelligence/Client_Docker/

<h4>
  Docker containers are utilized to avoid dependency issues
 <h4>
  
  
<h1>Connections<h1>
  
PORT | PROTOCOL | FUNCTION
------------|------------|------------
65432 | Socket | Stream Frames Client -> Server
50051 | GRPC | Send Start command Client -> Server

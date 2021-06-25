"""Command server for receiving grpc messages from HOST computer
Integrates a command class that defines how the data is structured.
Uses pickle to accept this class entry and will use to configure the rest of the robosub.

Server works as follows:
1. Server starts up and waits for GRPC connection.
2. On grpc packet arriving, unpacks and checks to see if a code or class data.
    if code 1: Returns acknowledge that the server is up and ready to receive class data.

    if class data: Unpickles and loads into command configuation packet.

Server Codes:
[1]: Acknowledge client and inform it is ready for class data.
[2]: Received class data.


3. Prints out the configuration data. This will eventually be changed such that intelligence
checks this data and initializes the right docker containers.
"""

from __future__ import print_function
from concurrent import futures
import sys
import grpc
import pickle

import src.utils.cmd_pb2 as cmd_pb2
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
from src.utils.command_configuration import CommandConfiguration as cmd

SERVER_PORT = 50052


class CommandGRPCServicer(cmd_pb2_grpc.CommandGRPCServicer):
    """Manages commands sent over grpc
    """
    def __init__(self):
        self.started = True
        self.config = None

    def SendCommandRequest(self, request, context):
        """Checks commands sent from client
        :param request: grpc message request
        :param context:
        :return: MsgReply
        """

        # First check data type of request
        request = request_to_value(str(request))
        if len(request) > 1:  # Check to see if CommandConfig obj is being sent or just a code
            request = bytes.fromhex(request)
            request = pickle.loads(request)
            # Load mission data
            config = cmd(socket_codes=[request.logging_code, request.video_code, request.telemetry_code],
                        pilot_control=request.pilot_control,
                        mission=request.mission)
            '''Here we can do anything we want with config sent from client. In this case we
            print it out, but it can be used to set intelligence's configuration for this run
            and start the correct docker containters.
            '''
            print(config)
            return cmd_pb2.MsgReply(ack='2')
        else:  # If we just receive a code, send acknowledge
            return cmd_pb2.MsgReply(ack='1')


def request_to_value(r):
    """Converts responses into strings. For some reason grpc adds quotes
    """
    first = -1
    result = ''
    for i in range(len(r)):
        if r[i] == '\"' and first == -1:
            first = i
        elif r[i] == '\"' and first != -1:
            result = r[first+1:i]
    return result


def main():
    """Driver code for command grpc server.
    This should be adapted and implemented into intelligence.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cmd_pb2_grpc.add_CommandGRPCServicer_to_server(CommandGRPCServicer(), server)
    server.add_insecure_port('[::]:' + str(SERVER_PORT))
    server.start()
    print('Started cmd grpc server.')
    server.wait_for_termination()


if __name__ == '__main__':
    main()
else:
    print('Run me as main!')
    sys.exit()

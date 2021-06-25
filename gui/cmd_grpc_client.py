"""Client for sending grpc commands from HOST to sub.
Integrates a command class that defines how the data is structured.
Uses pickle to send this class entry with provided arguments initializing 
class members to appropriate values.

This shall eventually be used by GUI but right now will be driver code for 
command communication testing.

Client works as follows:
1. Checks server is operating and sends code 1 and waits for acknowledge.
    On failure to acknowledge, terminates after 2s timeout.
2. On acknowledge, generates a CommandConfiguationPacket and encodes as
hex and sends. This is done as hex due to a problem with decoding messages
as bytes objects on the server end.
3. Waits for server to acknowledge sent CommandConfigurationPacket data
and terminates.

Client Codes:
[1]: Send to server to verify server is waiting.

Operation:
1. Start the server first.
2. Run this file. If you are network testing, modify main() for the correct
    IP and ports.

"""

from __future__ import print_function
import sys
import grpc
import pickle

import src.utils.cmd_pb2 as cmd_pb2
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
from src.utils.command_configuration import CommandConfiguration as cmd


class GrpcClient:
    """Handles grpc work.
    """
    def __init__(self, hostname, server_port):
        self.remote_client = hostname
        self.server_port = server_port
        self._channel = grpc.insecure_channel(str(self.remote_client) + ':' + str(self.server_port))
        self._stub = cmd_pb2_grpc.CommandGRPCStub(self._channel)

    def send(self, request):
        """Sends argument over grpc after casting to string.
        :param request: Sent over grpc
        """
        return self._stub.SendCommandRequest(cmd_pb2.MsgRequest(req=(str(request))))

    def __str__(self):
        return '<class grpc client> with host ' + str(self.remote_client) + ':' + str(self.server_port)


def response_to_value(r):
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
    """Driver code for the command grpc client.
    This should be adapted and implemented into HOST gui.
    """
    client = GrpcClient(hostname='localhost', server_port=50052)

    # Send a request to check for server
    try:
        response = client.send(1)
        print(str(response).strip())
    except grpc._channel._InactiveRpcError:
        print('Unable to connect to server, is it started?')
        sys.exit()
    if response_to_value(str(response)) == '1':  # If we have a valid grpc response, send config
        # Build a packet from config and serialize with pickle
        config = cmd(socket_codes=[1, 1, 1], pilot_control=True, mission='no')
        request = pickle.dumps(config.gen_packet()).hex()
        # Send packet
        response = client.send(request)
        print(str(response).strip())


if __name__ == '__main__':
    main()
else:
    print('Run me as main!')
    sys.exit()

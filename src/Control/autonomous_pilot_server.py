"""Implements a server for receiving autonomous directives local on the SUB.

The autonomous pilot server receives requests from the Intelligence container that give it abstracted instructions.
A few example instructions would be:
"thruster" "strafe" "port" -> strafe to port instruction
"thruster" "move" "forward" -> move to forward instruction
"thruster" "turn" "starboard" -> move to starboard instruction
"sensor" "read" "acceleration_x" -> return acceleration_x to intelligence

This server parses out the abstract instructions and translates them to actual instructions sent to the maestro or
values from sensors sent back to the intelligence subsystem.
"""

from __future__ import print_function
from concurrent import futures
import grpc
import multiprocessing as mp
import os
import sys
import struct
import socket

import src.Intelligence.cmd_grpc_server as grpc_server
import src.utils.cmd_pb2 as cmd_pb2
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
import src.utils.maestro_driver as maestro_driver
import src.utils.ip_config as ipc
ip = ipc.load_config_from_file('src/utils/ip_config.json')


SERVER_PORT = 50052


class CommandGRPCServicer(cmd_pb2_grpc.CommandGRPCServicer):
    """Manages commands sent over grpc
    """
    def __init__(self, pipe_out=None):
        self.pipe_out = pipe_out
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
            # Load instructions
            thruster_instruction = []
            # Pipe cmd to main
            if self.pipe_out is not None:
                self.pipe_out.send(('main', 'cmd_grpc', config.gen_packet()))
        # Send ack codes
            return cmd_pb2.MsgReply(ack='2')
        else:  # If we just receive a code, send acknowledge
            if request == '1':
                return cmd_pb2.MsgReply(ack='1')
            if (request == '2') and (self.pipe_out is not None):
                self.pipe_out.send(('main', 'cmd_grpc', 'kill_cmd'))
                return cmd_pb2.MsgReply(ack='3')


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




def run_server() -> None:
    """Server's driver code
    """
    dev = None  # Maestro device
    maestro = None  # Maestro object
    if (os.name != 'nt') and (len(sys.argv) > 1):  # Windows check and see if we got a device
        dev = sys.argv[1].replace(' ', '')
        maestro = maestro_driver.MaestroDriver(com_port=dev)
    started = True
    data = None
    payload_size = struct.calcsize('>6b')
    # Socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', ip.pilot_port))
        s.listen()
        conn, address = s.accept()
        while True:
            try:
                conn.sendall(b'1')  # Server ready to receive
            except BrokenPipeError:
                break  # HOST closed, restart this function to listen for new connection
            try:
                data = conn.recvfrom(1024)[0]
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
            except ConnectionAbortedError:
                break  # HOST closed, restart this function to listen for new connection
            if data is not None:
                data = struct.unpack('>6b', packed_msg_size)
                if dev is None:  # Print because we have no device
                    print(data)
                else:  # Have a device connected to this, send to Maestro
                    maestro.set_thrusts(data)


def run_grpc_server(pipe_in_from_main: any, pipe_out_to_main: any) -> None:
    """Run the GRPC server for receiving control inputs from intelligence
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[2] == 'initialize':
                started = True
        if started:
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            cmd_pb2_grpc.add_CommandGRPCServicer_to_server(grpc_server.CommandGRPCServicer(pipe_out=pipe_out_to_main),
                                                           server)
            server.add_insecure_port('[::]:' + str(ip.grpc_port))
            server.start()
            pipe_out_to_main.send(('main', 'cmd', 'started'))
            server.wait_for_termination()


def translate_to_bytes(list_to_bytes: list) -> bytes:
    for i in range(len(list_to_bytes)):
        list_to_bytes[i] += 100
    return bytes(list_to_bytes)


def translate_from_bytes(bytes_to_list: bytes) -> list:
    new_list = list(bytes_to_list)
    for i in range(len(new_list)):
        new_list[i] += -100
    return new_list


def main(start=False) -> None:
    """Control code to start and stop the server
    """
    while True:
        if not start:
            pass
        else:
            run_server()


if __name__ == '__main__':
    main(start=True)

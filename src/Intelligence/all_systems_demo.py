"""Quick and dirty demo of all subsystems concurrently communicating with GUI.
"""

from __future__ import print_function
from concurrent import futures
import grpc
import multiprocessing as mp
from multiprocessing import get_context, set_start_method
import os

import src.Intelligence.cmd_grpc_server as grpc_server
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
import src.utils.cmd_pb2 as cmd_pb2
from src.utils.command_configuration import CommandConfigurationPacket as cmd

import src.utils.ip_config as ipc
ip = ipc.load_config()


def cmd_process(pipe_in_from_main, pipe_out_to_main):
    """Command work
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[2] == 'initialize':
                started = True
        if started:  # CMD GRPC
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            cmd_pb2_grpc.add_CommandGRPCServicer_to_server(grpc_server.CommandGRPCServicer(pipe_out=pipe_out_to_main), server)
            server.add_insecure_port('[::]:' + str(ip.grpc_port))
            server.start()
            pipe_out_to_main.send(('main', 'cmd', 'started'))
            server.wait_for_termination()


def main():
    """Starts and handles processes
    """
    if os.name == 'nt':
        context = get_context('spawn')
    else:
        context = get_context('fork')
    cmd_pipe_to_main, pipe_in_from_cmd = context.Pipe()
    main_pipe_to_cmd, pipe_in_from_main = context.Pipe()
    proc_cmd = context.Process(target=cmd_process, args=(pipe_in_from_main, cmd_pipe_to_main))
    proc_cmd.start()
    main_pipe_to_cmd.send(('cmd', 'main', 'initialize'))
    while True:
        com = mp.connection.wait([pipe_in_from_cmd], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'cmd':
                if message[2] == 'started':
                    print('Started Command GRPC Server.')
            elif message[1] == 'cmd_grpc':
                print('Main received ' + str(message[2]))


if __name__ == '__main__':
    if os.name == 'nt':
        set_start_method('spawn')
    else:
        set_start_method('fork')
    print('Main process started at ' + str(os.getpid()))
    main()
else:
    print('Process started at ' + str(os.getpid()))

"""Quick and dirty demo of all subsystems concurrently communicating with GUI.
"""

from __future__ import print_function

import sys
import time
from concurrent import futures
import grpc
import multiprocessing as mp
from multiprocessing import get_context, set_start_method
import os
import logging
import docker

import src.Intelligence.cmd_grpc_server as grpc_server
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
from src.utils.command_configuration import CommandConfigurationPacket as cmdp
from src.utils.logger import LoggerServer

import src.utils.ip_config as ipc
ip = ipc.IPConfig(settings=[50052, 50001, 50002, 50003, 50004])

docker_client = docker.from_env()


def video_process(pipe_in_from_main, pipe_out_to_main):
    """Video work
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'main':
                if message[2] == 'initialize':
                    started = True
                    break
    if started:
        container = None
        containers = docker_client.containers.list(all=True)
        for i in range(len(containers)):
            if (containers[i].name == 'inf_video') and (os.name != 'nt'):  # Video only works on linux
                container = containers[i]
            elif (containers[i].name == 'inf_video') and (os.name == 'nt'):
                started = False
                break
        if container is not None:  # Start it
            container.start()
        while started:
            queue = mp.connection.wait([pipe_in_from_main], timeout=-1)
            if len(queue) > 0:
                message = queue[0].recv()
                if message[1] == 'main':
                    if message[2] == 'modify':
                        if message[3] == 'kill_cmd':
                            sys.exit(1)
                print(message)  # Can do other stuff here like modify container


def logging_process(logging_pipe, pipe_in_from_main, pipe_out_to_main):
    """Logging work
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'main':
                if message[2] == 'initialize':
                    started = True
                    break
    if started:
        container = None
        containers = docker_client.containers.list(all=True)
        for i in range(len(containers)):
            if containers[i].name == 'int_logging':  # Found our container
                container = containers[i]
        if container is not None:  # Start it
            container.start()
        while started:
            queue = mp.connection.wait([logging_pipe, pipe_in_from_main], timeout=-1)
            if len(queue) > 0:
                message = queue[0].recv()
                if message[1] == 'main':
                    if message[2] == 'modify':
                        if message[3] == 'kill_cmd':
                            sys.exit(1)
                print(message)  # Can do other stuff here like modify container


def telemetry_process(pipe_in_from_main, pipe_out_to_main):
    """Telemetry work
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'main':
                if message[2] == 'initialize':
                    started = True
                    break
    if started:
        container = None
        containers = docker_client.containers.list(all=True)
        for i in range(len(containers)):
            if containers[i].name == 'ctrl_telemetry':  # Found our container
                container = containers[i]
        if container is not None:  # Start it
            container.start()
        while started:
            queue = mp.connection.wait([pipe_in_from_main], timeout=-1)
            if len(queue) > 0:
                message = queue[0].recv()
                if message[1] == 'main':
                    if message[2] == 'modify':
                        if message[3] == 'kill_cmd':
                            sys.exit(1)
                print(message)  # Can do other stuff here like modify container


def pilot_process(pipe_in_from_main, pipe_out_to_main):
    """Pilot_Testing work
    """
    started = False
    while True:
        com = mp.connection.wait([pipe_in_from_main], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'main':
                if message[2] == 'initialize':
                    started = True
                    break
    if started:
        container = None
        containers = docker_client.containers.list(all=True)
        for i in range(len(containers)):
            if containers[i].name == 'ctrl_pilot':  # Found our container
                container = containers[i]
        if container is not None:  # Start it
            container.start()
        while started:
            queue = mp.connection.wait([pipe_in_from_main], timeout=-1)
            if len(queue) > 0:
                message = queue[0].recv()
                if message[1] == 'main':
                    if message[2] == 'modify':
                        if message[3] == 'kill_cmd':
                            sys.exit(1)
                print(message)  # Can do other stuff here like modify container


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
        if started:  # CMD GRPC server
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            cmd_pb2_grpc.add_CommandGRPCServicer_to_server(grpc_server.CommandGRPCServicer(pipe_out=pipe_out_to_main), server)
            server.add_insecure_port('[::]:' + str(ip.grpc_port))
            server.start()
            pipe_out_to_main.send(('main', 'cmd', 'started'))
            server.wait_for_termination()


def main():
    """Starts and handles processes
    """
    # OS compatability check
    if os.name == 'nt':
        context = get_context('spawn')
    else:
        context = get_context('fork')

    # Processes
    # Command process
    cmd_pipe_to_main, pipe_in_from_cmd = context.Pipe()
    main_pipe_to_cmd, pipe_in_from_main = context.Pipe()
    proc_cmd = context.Process(target=cmd_process, args=(pipe_in_from_main, cmd_pipe_to_main))
    proc_cmd.start()  # Start CMD process to listen for commands
    main_pipe_to_cmd.send(('cmd', 'main', 'initialize'))
    recv_cmd = None
    # Socket Processes
    video_pipe_to_main, pipe_in_from_video = context.Pipe()
    main_pipe_to_video, video_pipe_in_from_main = context.Pipe()
    # Generic logging pipe
    logging_pipe_out, logging_pipe_in = context.Pipe()
    logging_pipe_to_main, pipe_in_from_logging = context.Pipe()
    main_pipe_to_logging, logging_pipe_in_from_main = context.Pipe()
    telemetry_pipe_to_main, pipe_in_from_telemetry = context.Pipe()
    main_pipe_to_telemetry, telemetry_pipe_in_from_main = context.Pipe()
    pilot_pipe_to_main, pipe_in_from_pilot = context.Pipe()
    main_pipe_to_pilot, pilot_pipe_in_from_main = context.Pipe()
    proc_video = context.Process(target=video_process, args=(video_pipe_in_from_main, video_pipe_to_main))
    proc_logging = context.Process(target=logging_process, args=(logging_pipe_in, logging_pipe_in_from_main, logging_pipe_to_main))
    proc_telemetry = context.Process(target=telemetry_process, args=(telemetry_pipe_in_from_main, telemetry_pipe_to_main))
    proc_pilot = context.Process(target=pilot_process, args=(pilot_pipe_in_from_main, pilot_pipe_to_main))
    # Log queue test
    ls = LoggerServer(level=logging.DEBUG, save_logs=False)
    ls.log(prio=logging.DEBUG, subsystem='ASD-Main', message='Test debug.')
    ls.log(prio=logging.INFO, subsystem='ASD-Main', message='Test info.')
    ls.log(prio=logging.WARNING, subsystem='ASD-Main', message='Test warning.')
    ls.log(prio=logging.ERROR, subsystem='ASD-Main', message='Test error.')
    ls.log(prio=logging.CRITICAL, subsystem='ASD-Main', message='Test critical.')
    for i in ls.logging_queue:
        logging_pipe_out.send(('logging', 'main', 'log', ls.to_bytes()))
    while True:
        com = mp.connection.wait([pipe_in_from_cmd], timeout=-1)
        if len(com) > 0:
            message = com[0].recv()
            if message[1] == 'cmd':
                if message[2] == 'started':
                    print('Started Command GRPC Server.')
            elif message[1] == 'cmd_grpc':
                if isinstance(message[2], cmdp):  # Got a command config sent to main. GUI wants to enable sockets.
                    recv_cmd = message[2]
                elif message[2] == 'kill_cmd':  # Recieved kill command, kill all containers and exit
                    print('killing video')
                    main_pipe_to_video.send(('video', 'main', 'modify', 'kill_cmd'))
                    print('killing logging')
                    main_pipe_to_logging.send(('logging', 'main', 'modify', 'kill_cmd'))
                    print('killing telemetry')
                    main_pipe_to_telemetry.send(('telemetry', 'main', 'modify', 'kill_cmd'))
                    print('killing pilot')
                    main_pipe_to_pilot.send(('pilot', 'main', 'modify', 'kill_cmd'))
                    time.sleep(0.5)
                    print('killing system')
                    sys.exit(1)
        # If we have a command config then send messages to relevant sockets to enable
        if isinstance(recv_cmd, cmdp):
            # Logging
            if (recv_cmd.logging_code != 0) and (not proc_logging.is_alive()):  # Turn on logging process and socket
                proc_logging.start()
                print('Started Logger')
                # Send relevant logging level
                main_pipe_to_logging.send(('logging', 'main', 'initialize', recv_cmd.logging_code))
            elif proc_logging.is_alive():  # Send relevant modify code to change logging level
                main_pipe_to_logging.send(('logging', 'main', 'modify', recv_cmd.logging_code))
            # Video
            if (recv_cmd.video_code != 0) and (not proc_video.is_alive()):  # Turn on video process and socket
                proc_video.start()
                print('Started Video')
                # Send relevant video code
                main_pipe_to_video.send(('video', 'main', 'initialize', recv_cmd.video_code))
            elif proc_video.is_alive():
                main_pipe_to_video.send(('video', 'main', 'modify', recv_cmd.video_code))
            # Telemetry
            if (recv_cmd.telemetry_code != 0) and (not proc_telemetry.is_alive()):  # Turn on telemetry process and socket
                proc_telemetry.start()
                print('Started Telemetry')
                # Send relevant telemetry code
                main_pipe_to_telemetry.send(('telemetry', 'main', 'initialize', recv_cmd.telemetry_code))
            elif proc_telemetry.is_alive():
                main_pipe_to_telemetry.send(('telemetry', 'main', 'modify', recv_cmd.telemetry_code))
            # Pilot_Testing
            if recv_cmd.pilot_control and (not proc_pilot.is_alive()):  # Turn on pilot process and socket
                proc_pilot.start()
                print('Started Pilot_Testing')
                # Send if pilot is enabled
                main_pipe_to_pilot.send(('pilot', 'main', 'initialize', recv_cmd.pilot_control))
            elif proc_pilot.is_alive():
                main_pipe_to_pilot.send(('pilot', 'main', 'modify', recv_cmd.pilot_control))

            recv_cmd = None


if __name__ == '__main__':
    if os.name == 'nt':
        set_start_method('spawn')
    else:
        set_start_method('fork')
    print('Main process started at ' + str(os.getpid()))
    main()
else:
    print('Process started at ' + str(os.getpid()))

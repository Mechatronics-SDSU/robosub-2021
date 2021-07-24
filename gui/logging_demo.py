"""Demos a logging communication pathway between several processes.

Start this file first, then run the logging_client.
Check system.log after terminated.

Notes:
Linux compatability has been considered.

A more graceful solution down the line may help for parsing specific logs.
I've noticed that sometimes 2/3 messages will log on the same line.
I consider it something worth investigating for full release but works well enough for demo.

time.sleep calls are in the demo to differentiate between log messages.
These will be removed in an actual use case.
-Ian

Process Communication pathway:

                    =======
                    Control
                    =======
                     | (Pipe)
                     V
========= (socket) ======  (Pipe)   ============
   HOST     <---   Router   <---    Intelligence
=========          ======           ============
                     ^ (Pipe)
                     |
                    =========
                    Inference
                    =========
"""

import os
import sys
import multiprocessing as mp
from multiprocessing import set_start_method, get_context
import socket
import logging
import time

import src.utils.logger as logger
import src.utils.ip_config as ip_config
sys.modules['ip_config'] = ip_config
ipconfig = ip_config.load_config_from_file('src/utils/ip_config.json')


def sim_intelligence(pipe_to_router):
    """Simulates an intelligence process for logging.
    """
    ls_int = logger.LoggerServer(level=logging.DEBUG, save_logs=False)
    while True:
        ls_int.log(prio=logging.DEBUG, subsystem='Intelligence', message='Test Debug from Intelligence.')
        ls_int.log(prio=logging.INFO, subsystem='Intelligence', message='Test Info from Intelligence.')
        ls_int.log(prio=logging.WARN, subsystem='Intelligence', message='Test Warn from Intelligence.')
        ls_int.log(prio=logging.ERROR, subsystem='Intelligence', message='Test Error from Intelligence.')
        ls_int.log(prio=logging.CRITICAL, subsystem='Intelligence', message='Test Critical from Intelligence.')

        for i in ls_int.logging_queue:
            pipe_to_router.send(ls_int.to_bytes())

        time.sleep(5)


def sim_inference(pipe_to_router):
    """Simulates an inference process for logging.
    """
    ls_inf = logger.LoggerServer(level=logging.DEBUG, save_logs=False)
    while True:
        ls_inf.log(prio=logging.DEBUG, subsystem='Inference', message='Test Debug from Inference.')
        ls_inf.log(prio=logging.INFO, subsystem='Inference', message='Test Info from Inference.')
        ls_inf.log(prio=logging.WARN, subsystem='Inference', message='Test Warn from Inference.')
        ls_inf.log(prio=logging.ERROR, subsystem='Inference', message='Test Error from Inference.')
        ls_inf.log(prio=logging.CRITICAL, subsystem='Inference', message='Test Critical from Inference.')

        for i in ls_inf.logging_queue:
            pipe_to_router.send(ls_inf.to_bytes())

        time.sleep(5)


def sim_control(pipe_to_router):
    """Simulates a control process for logging.
    """
    ls_ctrl = logger.LoggerServer(level=logging.DEBUG, save_logs=False)
    while True:
        ls_ctrl.log(prio=logging.DEBUG, subsystem='Control', message='Test Debug from Control.')
        ls_ctrl.log(prio=logging.INFO, subsystem='Control', message='Test Info from Control.')
        ls_ctrl.log(prio=logging.WARN, subsystem='Control', message='Test Warn from Control.')
        ls_ctrl.log(prio=logging.ERROR, subsystem='Control', message='Test Error from Control.')
        ls_ctrl.log(prio=logging.CRITICAL, subsystem='Control', message='Test Critical from Control.')

        for i in ls_ctrl.logging_queue:
            pipe_to_router.send(ls_ctrl.to_bytes())

        time.sleep(5)


def out_router(ports, intelligence_pipe, inference_pipe, control_pipe):
    """Sends all logged messages to the client.
    """
    # Socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', 50002))  # TODO change this back to using config.pickle, hard coded here because it breaks container
        s.listen()
        conn, address = s.accept()
        while True:
            queue = mp.connection.wait([intelligence_pipe, inference_pipe, control_pipe], timeout=-1)
            if len(queue) > 0:
                result = conn.recvfrom(1024)[0]
                if result == b'1':
                    log = queue[0].recv()
                    conn.sendall(log)


def main():
    """Driver code and entry point.
    """
    if os.name == 'nt':
        context = get_context('spawn')
    else:
        context = get_context('fork')

    # Logger pipes
    # Intelligence
    pipe_to_router_from_intelligence, pipe_in_from_intelligence = context.Pipe()
    # Inference
    pipe_to_router_from_inference, pipe_in_from_inference = context.Pipe()
    # Control
    pipe_to_router_from_control, pipe_in_from_control = context.Pipe()

    # Processes
    router_proc = context.Process(target=out_router, args=(ipconfig,
                                                           pipe_in_from_intelligence,
                                                           pipe_in_from_inference,
                                                           pipe_in_from_control))
    intelligence_proc = context.Process(target=sim_intelligence, args=(pipe_to_router_from_intelligence,))
    inference_proc = context.Process(target=sim_inference, args=(pipe_to_router_from_inference,))
    control_proc = context.Process(target=sim_control, args=(pipe_to_router_from_control,))

    router_proc.start()

    intelligence_proc.start()
    inference_proc.start()
    control_proc.start()


if __name__ == '__main__':
    n = os.name
    if n == 'nt':
        set_start_method('spawn')
    else:
        set_start_method('fork')
    print(__name__ + 'started on ' + n + ' at ' + str(os.getpid()))
    main()
else:
    print('Child process created at ' + str(os.getpid()))

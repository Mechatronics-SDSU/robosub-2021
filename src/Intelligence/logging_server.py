"""Logging Server demo.
Demonstrates a logging implementation over socket. The socket is run in its own process and the main method pipes
log input as bytes to the server to be sent to a client.
See logger.py for more information.
"""

import multiprocessing as mp
from multiprocessing import set_start_method, get_context
import os
import socket
import logging
import time

from logger import LoggerServer

SERVER_HOSTNAME = ''
SERVER_PORT = 50002


def logging_server(pipe_in):
    """Sends logs over socket after receiving them over an input pipe.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SERVER_HOSTNAME, SERVER_PORT))
        s.listen(5)
        conn, address = s.accept()
        while True:
            queue = mp.connection.wait([pipe_in], timeout=-1)
            if len(queue) > 0:  # New log received, send to conected client
                log = queue[0].recv()
                print(log)
                conn.sendall(log)


def main():
    """Logging server driver code
    """
    context = get_context('spawn')
    pipe_to_server, pipe_in_server = context.Pipe()
    logging_server_proc = context.Process(target=logging_server, args=(pipe_in_server, ))
    logging_server_proc.start()

    # Demo of logger
    ls = LoggerServer(level=logging.DEBUG)
    while True:
        ls.log(prio=logging.DEBUG, subsystem='Intelligence', message='Test debug.')
        ls.log(prio=logging.INFO, subsystem='Intelligence', message='Test info.')
        ls.log(prio=logging.WARNING, subsystem='Intelligence', message='Test warning.')
        ls.log(prio=logging.ERROR, subsystem='Intelligence', message='Test error.')
        ls.log(prio=logging.CRITICAL, subsystem='Intelligence', message='Test critical.')

        for i in ls.logging_queue:
            pipe_to_server.send(ls.to_bytes())

        time.sleep(5)  # JUST FOR DEMO PURPOSES

    # logging_server_proc.join()


if __name__ == '__main__':
    set_start_method('spawn')
    print('Main process started at ' + str(os.getpid()))
    main()
else:
    print('Child process started at ' + str(os.getpid()))

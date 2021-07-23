"""Implements a client for receiving pilot control input on the SUB.

Pilot client accepts a socket connection and receives controller input from HOST.
This is encapsulated in a Controller object for convenient method access with
options for configurations.

Developed and tested with Ian's Xbox One Controller but other configuations can
be added at a later time.

Controller Note:
Because not all controllers are made with the same layouts for the right button pad,
they are named N S E W in the class, as to represent a compass.
This is to prevent confusion between different configurations and mappings.
"""

from __future__ import print_function
import sys
import socket
import struct


port = 50004


def run_client():
    """Client's driver code
    """
    started = True
    data = None
    payload_size = struct.calcsize('>6b')
    # Socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', port))
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
                print(data)
                '''Here we can do whatever we want with this array.
                Here it is printed but it can be used for maestro control.
                '''


def main(start=False):
    """Control code to start and stop the server
    """
    while True:
        if not start:
            pass
        else:
            run_client()


if __name__ == '__main__':
    main(start=True)
else:
    sys.exit()

"""Driver code to receive telemetry from SUB.

Unlike telemetry_server, this will work with both random and real data unmodified and can be implemented
to HOST gui as is.
"""

from __future__ import print_function
import socket

from telemetry import Telemetry

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 50004


def run_client():
    """Client's driver code
    """
    '''Right now we just print out the server's sensor data. This will be implemented into gui on HOST.
    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((SERVER_ADDRESS, SERVER_PORT))
        while True:
            s.sendall(b'1')
            data = s.recv(4096)
            tel = Telemetry()
            tel.load_data_from_bytes(data)
            print(tel.sensors)


def main(start=False):
    """Control code to start and stop the client
    """
    while True:
        if not start:
            pass
        else:
            run_client()


if __name__ == '__main__':
    main(start=True)

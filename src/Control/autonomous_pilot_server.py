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
import grpc
import os
import sys
import struct
import socket

import src.utils.maestro_driver as maestro_driver
import src.utils.ip_config as ipc
ip = ipc.load_config_from_file('src/utils/ip_config.json')


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


def run_grpc_server() -> None:
    """Run the GRPC server for receiving control inputs from intelligence
    """
    pass


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
else:
    sys.exit()

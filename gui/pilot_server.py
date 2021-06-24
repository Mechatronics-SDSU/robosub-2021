"""Implements a server for pilot control on the HOST computer.

Pilot server accepts controller input using pygame's Joystick library, puts it into a numpy array,
and then sends it over a socket connection after converting it to bytes.

This is hosted on the HOST end, rather than the sub, because the HOST machine will be accepting the
controller inputs.

Instructions:

1. Run the server. (This file)
2. Press a button on the controller. This starts the pygame event pump.
3. Start the client.

Tested on Ian's Xbox One Controller.
"""

from __future__ import print_function
import sys
import socket

import numpy as np
import pygame as pg

started = True
hostname = ''
port = 50003


def run_server():
    """Server's driver code
    """
    # Pygame
    pg.init()
    pg.joystick.init()
    js = pg.joystick.Joystick(0)
    js.init()

    if js.get_init():
        pass
        """
        # Test code to show controller info. Uncomment and test at one's own discretion.
        print(js.get_name())
        print('Number of axes: ' + str(js.get_numaxes()))
        print('Number of balls: ' + str(js.get_numballs()))
        print('Number of buttons: ' + str(js.get_numbuttons()))
        print('Number of hats: ' + str(js.get_numhats()))
        print('\n')
        """

    # Socket connection
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((hostname, port))
        s.listen(5)
        conn, address = s.accept()
        while started:
            result = conn.recvfrom(1024)[0]
            if result == b'1':  # Client requests data

                # Get pygame data, throw it into a numpy array
                pg.event.pump()  # Called each loop to poll for new inputs
                control_in = np.zeros(shape=(1, (js.get_numaxes()
                                                 + js.get_numbuttons()
                                                 + js.get_numhats())))
                for i in range(js.get_numaxes()):  # Axes
                    control_in.put(i, js.get_axis(i))
                for i in range(js.get_numaxes(), js.get_numbuttons()):  # Buttons
                    control_in.put(i, js.get_button(i - js.get_numaxes()))
                control_in.put((js.get_numaxes() + js.get_numbuttons()), js.get_hat(0))  # Hat

                # Send it
                conn.sendall(control_in.tobytes())


def main(start=False):
    """Control code to start and stop the server
    """
    # Wait for signal from some other method to start server
    while True:
        if not start:
            pass
        else:
            run_server()


if __name__ == '__main__':
    main(start=True)
else:
    sys.exit()

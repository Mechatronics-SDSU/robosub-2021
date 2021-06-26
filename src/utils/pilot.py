"""Pilot_client class moved to here.
Sets the config of the joystick.

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

import numpy as np
import pygame


started = True
server_name = 'localhost'
port = 50003


class Controller:
    """Configuration of the HOST's controller
    """
    def __init__(self, name):
        # Name of controller
        self.name = name
        # Indicies in for where each button/axis is in numpy array
        # Axes
        self.L_JOY_X = 0
        self.L_JOY_Y = 0
        self.R_JOY_X = 0
        self.R_JOY_Y = 0
        self.L2 = 0
        self.R2 = 0
        # Buttons
        self.L1 = 0
        self.R1 = 0
        self.N_BUTTON = 0
        self.S_BUTTON = 0
        self.E_BUTTON = 0
        self.W_BUTTON = 0

        self.state = None

        self.setup_defaults()

    def setup_defaults(self):
        """Map buttons to the specified controller.
        """
        if self.name == 'XBONE':
            # Axes
            self.L_JOY_X = 0
            self.L_JOY_Y = 1
            self.R_JOY_X = 2
            self.R_JOY_Y = 3
            self.L2 = 4
            self.R2 = 5
            # Buttons
            self.L1 = 10
            self.R1 = 11
            self.N_BUTTON = 9
            self.S_BUTTON = 6
            self.E_BUTTON = 7
            self.W_BUTTON = 8
            # Hat ignored for now, was having issues reading it
            return True
        elif self.name == 'PS4':
            # I don't have a PS4 controller to test this.
            return False
        else:
            return False

    def set_state(self, numpy_array):
        """Sets button state to the input array.
        """
        self.state = numpy_array

    def get_state(self):
        """Shows current button state.
        :return:
        """
        if self.state is None:
            return None
        else:
            return self.state

    def __str__(self):
        return str(self.name) + \
               ' Controller object. '

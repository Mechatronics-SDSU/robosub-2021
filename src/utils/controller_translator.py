"""Translates raw control inputs from pygame into ESC instructions

Maestro values: Anything from -100 to 100
-100 is assumed to be down for Z thrusters, +100 is assumed to be up for Z thrusters
Order of array to send to Maestro:
[Port Forward Z Thruster,
Starboard Forward Z Thruster,
Starboard Y Thruster,
Starboard Aft Z Thruster,
Port Aft Z Thruster,
Port Y Thruster]

[PFZT, SFZT, SYT, SAZT, PAZT, PTY]
Diagram:
                                     Bow
    Port Forward Z Thurster PFZT -> 0===0 <- Starboard Forward Z Thurster SFZT
                                      |
              Port Y Thruster PYT -> 0|0 <- Starboard Y Thruster SYT
                                      |
        Port Aft Z Thurster PAZT -> 0===0 <- Starboard Aft Z Thruster SAZT
                                    Stern
"""

import math
import numpy as np


class ControllerTranslator:
    """Gets controller state as a numpy array and translates it into controls sent to the maestro.
    """
    def __init__(self, offset=0, invert_controls=False):
        self.invert = invert_controls
        self.offset = offset  # amount to offset ESCs by when performing translation.
        # Ex. ESC needs value of 50 to begin moving thrusters. Offset of 49 means 0 is mapped to 49.

    def translate_to_maestro_controller(self, inputs):
        """Accepts a numpy array from pygame controller, translates into maestro instructions.
        :return: list of instructions for the maestro
        """
        # Base values, default to 0 for non moving state
        result_x = 0.0  # Function of LJ/RJ
        result_y = 0.0  # Function of LJ/RJ
        result_z = 0.0  # Function of L2/R2
        result = [0, 0, 0, 0, 0, 0]
        # Z
        L2 = inputs[0][4]
        R2 = inputs[0][5]
        # XY
        LJ_X = inputs[0][0]
        LJ_Y = inputs[0][1]
        RJ_X = inputs[0][2]
        RJ_Y = inputs[0][3]

        # Calculate Z
        z_abs = 0
        z_dir = 0
        # L2 and R2 are mutually exclusive, one > -1 means other is -1.
        # Shift from range -1, 1 to 0, 2 such that -1 is mapped to 0 for rest state
        if L2 > -1:
            L2 += 1
            z_abs = L2 / 2  # Divide by 2 to get range from 0, 1
            z_dir = 1  # L2 mapped to up
        else:
            R2 += 1
            z_abs = R2 / 2  # Divide by 2 to get range from 0, 1
            z_dir = -1  # R2 mapped to down
        # z_abs now a percentile of how far to move, z_dir is positive if up and negative if down

        # Cartesian quadrant the joysticks are in
        quadrant_LJ = 0
        quadrant_RJ = 0
        if (LJ_X >= 0) and (LJ_Y >= 0):
            quadrant_LJ = 1
        elif (LJ_X < 0) and (LJ_Y >= 0):
            quadrant_LJ = 2
        elif (LJ_X < 0) and (LJ_Y < 0):
            quadrant_LJ = 3
        else:
            quadrant_LJ = 4
        if (RJ_X >= 0) and (RJ_Y >= 0):
            quadrant_RJ = 1
        elif (RJ_X < 0) and (RJ_Y >= 0):
            quadrant_RJ = 2
        elif (RJ_X < 0) and (RJ_Y < 0):
            quadrant_RJ = 3
        else:
            quadrant_RJ = 4

        # Translate
        # SYT/PYT is a function of LJY only
        SYT = 0
        PYT = 0
        if (quadrant_LJ == 1) or (quadrant_LJ == 2):  # Go forward
            delta = 100 - self.offset
            if delta < 100:  # Map proportionally starting at offset instead of 0
                SYT = self.offset + math.floor(LJ_Y * delta)
            else:
                SYT = math.floor(LJ_Y * 100)
        else:  # Go backward
            delta = -100 + self.offset
            if delta > -100:  # Map proportionally starting at offset instead of 0
                SYT = self.offset + math.ceil(LJ_Y * delta)
            else:
                SYT = math.ceil(LJ_Y * -100)
        PYT = SYT  # Y Thrusters should always be the same values for forward/backward

        # PFZT, SFZT, SAZT, PAZT are a function of LJ_X, RJ_X, and L2/R2
        PFZT = 0
        SFZT = 0
        SAZT = 0
        PAZT = 0

        # Add some kind of trig function here?

        return [PFZT, SFZT, SYT, SAZT, PAZT, PYT]

    def translate_to_maestro_intelligence(self):
        """Accepts instructions sent from intelligence, translates into maestro instructions.
        """
        pass


def _driver_test_code():
    """Test code using controller inputs directly. Don't run in other modules!
    """
    import pygame as pg
    pg.init()
    pg.joystick.init()
    js = pg.joystick.Joystick(0)
    print(js)


if __name__ == '__main__':
    _driver_test_code()
else:
    print('Initialized Controller Translator module')

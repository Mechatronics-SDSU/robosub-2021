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

    def __init__(self,
                 offset=0,
                 invert_controls=False,
                 joystick_drift_compensation=0.05,
                 base_net_turn=0,
                 z_drift_compensation=0,
                 base_net_strafe=0):
        self.invert = invert_controls
        self.joystick_drift_compensation = joystick_drift_compensation
        self.base_net_turn = base_net_turn
        self.z_drift_compensation = z_drift_compensation
        self.base_net_strafe = base_net_strafe
        self.offset = offset  # amount to offset ESCs by when performing translation
        # Ex. ESC needs value of 50 to begin moving thrusters. Offset of 49 means 0 is mapped to 49

    def translate_to_maestro_controller(self, inputs) -> list:
        """Accepts a numpy array from pygame controller, translates into maestro instructions.
        :return: list of instructions for the maestro
        """

        # Z
        L2 = inputs[0][4]
        R2 = inputs[0][5]
        # XY
        LJ_X = inputs[0][0]
        LJ_Y = inputs[0][1]
        RJ_X = inputs[0][2]
        RJ_Y = inputs[0][3]  # Currently unused

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
        if ((LJ_X >= 0) and (LJ_Y < 0)) and \
                ((LJ_X > self.joystick_drift_compensation) or (math.fabs(LJ_Y) > self.joystick_drift_compensation)):
            quadrant_LJ = 1
        elif ((LJ_X < 0) and (LJ_Y < 0)) and \
                ((math.fabs(LJ_X) > self.joystick_drift_compensation) or (math.fabs(LJ_Y) > self.joystick_drift_compensation)):
            quadrant_LJ = 2
        elif ((LJ_X < 0) and (LJ_Y >= 0)) and \
                ((math.fabs(LJ_X) > self.joystick_drift_compensation) or (LJ_Y > self.joystick_drift_compensation)):
            quadrant_LJ = 3
        elif ((LJ_X >= 0) and (LJ_Y >= 0)) and \
                ((LJ_X > self.joystick_drift_compensation) or (LJ_Y > self.joystick_drift_compensation)):
            quadrant_LJ = 4

        # Translate

        # SYT/PYT is a function of LJY and RJX
        SYT = 0
        PYT = 0
        delta = 100 - self.offset
        if ((quadrant_LJ == 1) or (quadrant_LJ == 2)) and (math.fabs(RJ_X) <= self.joystick_drift_compensation):  # Forward
            if delta < 100:  # Map proportionally starting at offset instead of 0
                SYT = self.offset + math.floor(math.fabs(LJ_Y) * delta)
            else:
                SYT = math.floor(math.fabs(LJ_Y) * 100)
            PYT = SYT  # Going forward, both motors should be same values
        elif ((quadrant_LJ == 3) or (quadrant_LJ == 4)) and (math.fabs(RJ_X) <= self.joystick_drift_compensation):  # Backward
            if delta < 100:
                SYT = self.offset + math.ceil(-1 * LJ_Y * delta)
            else:
                SYT = math.ceil(-1 * LJ_Y * 100)
            PYT = SYT
        elif ((quadrant_LJ == 1) or (quadrant_LJ == 2)) and (RJ_X > self.joystick_drift_compensation):  # Turn to starboard
            if delta < 100:
                net_turn = LJ_Y - RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    SYT = self.offset + math.floor(net_turn * delta)
                else:
                    SYT = self.base_net_turn
                PYT = self.offset + math.ceil(-1 * LJ_Y * delta)
            else:
                net_turn = LJ_Y - RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    SYT = math.floor(net_turn * 100)
                else:
                    SYT = self.base_net_turn
                PYT = math.ceil(-1 * LJ_Y * 100)
        elif ((quadrant_LJ == 1) or (quadrant_LJ == 2)) and (RJ_X < (-1 * self.joystick_drift_compensation)):  # Turn to port
            if delta < 100:
                net_turn = LJ_Y + RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    PYT = self.offset + math.floor(net_turn * delta)
                else:
                    PYT = self.base_net_turn
                SYT = self.offset + math.ceil(-1 * LJ_Y * delta)
            else:
                net_turn = LJ_Y + RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    PYT = math.floor(net_turn * 100)
                else:
                    PYT = self.base_net_turn
                SYT = math.ceil(-1 * LJ_Y * 100)
        elif ((quadrant_LJ == 3) or (quadrant_LJ == 4)) and (RJ_X > self.joystick_drift_compensation):  # Inverted turn to port
            if delta < 100:
                net_turn = (-1 * LJ_Y) - RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    SYT = self.offset + (-1 * math.floor(net_turn * delta))
                else:
                    SYT = self.base_net_turn
                PYT = math.ceil(LJ_Y * delta)
            else:
                net_turn = (-1 * LJ_Y) - RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    SYT = math.floor(net_turn * 100)
                else:
                    SYT = self.base_net_turn
                PYT = math.floor(LJ_Y * 100)
        elif ((quadrant_LJ == 3) or (quadrant_LJ == 4)) and (RJ_X < (-1 * self.joystick_drift_compensation)):  # Inverted turn to starboard
            if delta < 100:
                net_turn = (-1 * LJ_Y) + RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    PYT = (-1 * math.floor(net_turn * delta))
                else:
                    PYT = self.base_net_turn
                SYT = math.ceil(LJ_Y * delta)
            else:
                net_turn = (-1 * LJ_Y) + RJ_X + self.base_net_turn
                if net_turn >= self.base_net_turn:
                    if net_turn > 1:
                        net_turn = 1
                    PYT = -1 * math.floor(net_turn * 100)
                else:
                    PYT = self.base_net_turn
                SYT = math.ceil(LJ_Y * 100)
        elif (math.fabs(RJ_X) > self.joystick_drift_compensation) and (RJ_X > 0):  # Turn in-place to starboard
            if delta < 100:
                SYT = self.offset + math.ceil(RJ_X * -1 * delta)  # Reverse on Starboard Y Thruster
                PYT = self.offset + math.floor(RJ_X * delta)  # Forward on Port Y Thruster
            else:
                SYT = math.ceil(RJ_X * -100)
                PYT = math.floor(RJ_X * 100)
        elif (math.fabs(RJ_X) > self.joystick_drift_compensation) and (RJ_X < 0):  # Turn in-place to port
            if delta < 100:
                SYT = self.offset + math.floor(RJ_X * -1 * delta)  # Forward on Starboard Y Thruster
                PYT = self.offset + math.ceil(RJ_X * delta)  # Reverse on Port Y Thruster
            else:
                SYT = math.floor(RJ_X * -100)
                PYT = math.ceil(RJ_X * 100)
        else:  # No movement
            SYT = 0
            PYT = 0

        # PFZT, SFZT, SAZT, PAZT are a function of LJ_X and L2/R2
        PFZT = 0
        SFZT = 0
        SAZT = 0
        PAZT = 0

        if (z_abs > self.z_drift_compensation) and (z_dir == 1):  # Ascend
            PFZT = SFZT = SAZT = PAZT = math.floor(100 * z_abs)
        elif (z_abs > self.z_drift_compensation) and (z_dir == -1):  # Descend
            PFZT = SFZT = SAZT = PAZT = math.ceil(-100 * z_abs)
        elif (LJ_X > self.joystick_drift_compensation) and (z_abs <= self.z_drift_compensation):  # Strafe to Starboard
            if delta < 100:
                SFZT = SAZT = (-1 * self.offset) + math.ceil(LJ_X * -1 * delta)
                PAZT = PFZT = (-1 * self.offset) + self.base_net_strafe
            else:
                SFZT = SAZT = math.ceil(LJ_X * -100)
                PAZT = PFZT = math.ceil(self.base_net_strafe)
        elif ((-1 * LJ_X) > self.joystick_drift_compensation) and (z_abs <= self.z_drift_compensation):  # Strafe to Port
            if delta < 100:
                PAZT = PFZT = (-1 * self.offset) + math.ceil(LJ_X * -1 * delta)
                SFZT = SAZT = (-1 * self.offset) + self.base_net_strafe
            else:
                PAZT = PFZT = math.ceil(LJ_X * 100)
                SFZT = SAZT = math.ceil(self.base_net_strafe)

        return [PFZT, SFZT, SYT, SAZT, PAZT, PYT]

    def translate_to_maestro_intelligence(self):
        """Accepts instructions sent from intelligence, translates into maestro instructions.
        (Might not need this?)
        """
        pass


def _driver_test_code() -> None:
    """Test code using controller inputs directly. Don't run in other modules!
    """
    import pygame as pg
    pg.init()
    pg.joystick.init()
    js = pg.joystick.Joystick(0)
    js.init()
    print(str(js.get_numaxes()) + ' ' + str(js.get_numbuttons()) + ' ' + str(js.get_numhats()))
    ct = ControllerTranslator(joystick_drift_compensation=0.1, base_net_turn=10, base_net_strafe=-20)
    while True:
        if js.get_init():
            control_in = np.zeros(shape=(1, js.get_numaxes()
                                        + js.get_numbuttons()
                                        + js.get_numhats()))
            for i in range(js.get_numaxes()):
                control_in.put(i, js.get_axis(i))
            for i in range(js.get_numaxes(), js.get_numbuttons()):  # Buttons
                control_in.put(i, js.get_button(i - js.get_numaxes()))

            control_in.put((js.get_numaxes() + js.get_numbuttons()), js.get_hat(0))  # Hat
            print(ct.translate_to_maestro_controller(control_in))
        pg.event.pump()


if __name__ == '__main__':
    _driver_test_code()
else:
    print('Initialized Controller Translator module')

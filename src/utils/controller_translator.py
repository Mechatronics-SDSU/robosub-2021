"""Translates raw control inputs from pygame into ESC instructions
"""

import math
import numpy as np


class ControllerTranslator:
    """Gets controller state as a numpy array and translates it into controls sent to the maestro.
    """
    def __init__(self, offset=0):
        self.offset = offset

    def translate_to_maestro_controller(self, inputs):
        """Accepts a numpy array from pygame controller, translates into maestro instructions.
        :return: list of instructions for the maestro
        """
        if self.offset == 0:
            pass
        else:
            pass
        result_x = 0.0  # Function of LJ/RJ
        result_y = 0.0  # Function of LJ/RJ
        result_z = 0.0  # Function of L2/R2
        L2 = inputs[0][4]
        R2 = inputs[0][5]

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

"""
Bounding Box class used to return a box's properties to intelligence.

Contributers:
Ian Reichard
"""

import sys
import math


class Box:
    """
    Properties of the rectangle's bounding box.
    """

    def __init__(self, x_top, y_top, x_bot, y_bot):
        """
        :param x_top: The box's top left x coordinate.
        :param y_top: The box's top left y coordinate.
        :param x_bot: The box's bottom right x coordinate.
        :param y_bot: The box's bottom right y coordinate.
        """
        self.upper_x = x_top
        self.upper_y = y_top
        self.lower_x = x_bot
        self.lower_y = y_bot
        self.width = math.floor(math.fabs(self.lower_x - self.upper_x))
        if self.width < 0:
            self.width = 0
        self.height = math.floor(math.fabs(self.lower_y - self.upper_y))
        if self.height < 0:
            self.height = 0

    def get_coordinates(self):
        """
        Gets bounding box information as 2 coordinates.
        (First coordinate)  X________
                            |       |
                            |       |
                            |_______X (Second coordinate)
        :return:[x_left, y_top, x_right, y_bottom]
        """
        return [self.upper_x, self.upper_y, self.lower_x, self.lower_y]

    def get_area(self):
        """
        Returns the size of the image.
        """
        return self.width * self.height


if __name__ != '__main__':
    print('Box class initialized!')
else:
    print('Import me!')
    sys.exit()

"""
Bounding Box class used to return a box's properties to intelligence.

Contributers:
Ian Reichard
"""

import sys


class Box:
    """
    Properties of the rectangle's bounding box.
    """

    def __init__(self, w, h, x_top, y_bot):
        """
        :param w: The box's width
        :param h: The box's height
        :param x_top: The box's upper left x coordinate.
        :param y_bot: The box's bottom right y coordinate.
        """

        self.width = w
        self.height = h
        self.upper = x_top
        self.lower = y_bot

    def get_coordinates(self):
        """
        Gets bounding box information as 2 coordinates.
        (First coordinate)  X________
                            |       |
                            |       |
                            |_______X (Second coordinate)
        :return:[x_left, y_top, x_right, y_bottom]
        """
        if self.lower-self.height < 0:
            return [self.upper, self.upper+self.width, self.lower-self.height, self.lower]
        else:
            return [self.upper, self.upper + self.width, 0, self.lower]

    def get_area(self):
        """
        Returns the size of the image.
        """
        return self.width * self.height


if __name__ != '__main__':
    print('Box class initialized!')
else:
    print('Don\'t import me!')
    sys.exit()

"""TODO: Add a docstring!
"""
import cv2
import numpy as np
import math
import datetime
from utils.consants import (RADIUS, RED, BLACK, WHITE, BLUE)


class DetectedObject:
    """TODO: Add a docstring!
    """
    def __init__(self, object_id, box, score=None):
        self.id = [object_id]  # post, two-posts, left-corner, right-corner, full-gate, buoy1, buoy2,
        self.box = box
        self.score = [score]
        self.distance = self.__get_estimated_distance_to_gate()

    def __get_estimated_distance_to_gate(self):
        """
        :return: Estimated distance to the detected gate
        """
        gate_height = abs(self.box[3] - self.box[1])
        return round(1000 / gate_height, 2)


class FPS:
    """TODO: Add a docstring!
    """
    def __init__(self):
        self._start = None
        self._end = None
        self._numFrames = 0

    def start(self):
        """TODO: Add a docstring!
        """
        self._start = datetime.datetime.now()
        return self

    def stop(self):
        """TODO: Add a docstring!
        """
        self._end = datetime.datetime.now()

    def update(self):
        """
        increment the total number of frames examined during the start and end intervals
        """
        self._numFrames += 1

    def elapsed(self):
        """
        :return: total number of seconds between the start and end interval
        """
        return (self._end - self._start).total_seconds()

    def fps(self):
        """
        :return: the (approximate) frames per second
        """
        return self._numFrames / self.elapsed()

    @staticmethod
    def display_fps(self, frame, fps):
        """TODO: Add a docstring!
        """
        cv2.putText(frame, f'FPS: {round(fps, 2)}', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2, cv2.LINE_AA)


def distance_between_points(p1, p2):
    """
    :return: Distance between the two given points
    """
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def rectangle_to_point(rectangle):
    """
    :param rectangle: rectangle of the format x1, y1, x2, y2
    :return: the mid point of the given rectangle as well as old points
    """
    xmin, ymin, xmax, ymax = rectangle
    x, y = (xmin + xmax) // 2, (ymin + ymax) // 2
    point = (x, y)
    old_points = np.array([[x, y]], dtype=np.float32)
    return point, old_points


def point_to_rectangle(x, y, w, h):
    """
    :param x: point x coordinate
    :param y: point y coordinate
    :param w: rectangle width
    :param h: rectangle height
    :return: rectangle coordinates
    """
    x1 = x - RADIUS - (w // 2)
    y1 = y - RADIUS - (h // 2)
    x2 = x + RADIUS + (w // 2)
    y2 = y + RADIUS + (h // 2)
    return x1, y1, x2, y2


def draw_point(frame, x, y):
    """
    :param frame: frame to draw on
    :param x: X coordinate of the point
    :param y: Y coordinate of the point
    """
    cv2.circle(frame, (x, y), RADIUS, RED, -1)


def draw_rect(frame, rect, color):
    """
    :param frame: frame to draw on
    :param rect: coordinates of rectangle to draw (x1, y1, x2, y2)
    :param color: desired color to draw the rectangle in
    """
    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)


def draw_lines(frame, lines, color):
    """
    :param frame: frame to draw on
    :param lines: 2D array of lines to draw
    :param color: desired color to draw the lines in
    """
    for line in lines:
        x1, y1, x2, y2 = line
        cv2.line(frame, (x1, y1), (x2, y2), color, 2)


def draw_detected_object(frame, detected_object, color):
    """
    :param frame: frame to draw on
    :param detected_object: detected object class instance
    :param color: color to draw tracking boxes with
    """
    x1, y1, x2, y2 = detected_object.box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = f'ID: {" ".join(detected_object.id)}  Score: {detected_object.score}  Distance: {detected_object.distance}'
    label_size, base_line = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    label_ymin = max(y1, label_size[1] + 8)
    cv2.rectangle(frame, (x1, label_ymin - label_size[1] - 8), (x1 + label_size[0], label_ymin + base_line - 8),
                  BLACK, cv2.FILLED)
    cv2.putText(frame, label, (x1, label_ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)

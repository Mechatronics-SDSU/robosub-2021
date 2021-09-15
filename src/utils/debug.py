"""TODO: Add a docstring!
"""
import cv2


def draw_lines(src, lines, color):
    """TODO: Add a docstring!
    """
    for line in lines:
        x1, y1, x2, y2 = line
        cv2.line(src, (x1, y1), (x2, y2), color, 2)


def draw_detected_tracking_boxes(src, tracking_boxes, color):
    """TODO: Add a docstring!
    """
    for tracking_box in tracking_boxes:
        x1, y1, x2, y2 = tracking_box.box
        cv2.rectangle(src, (x1, y1), (x2, y2), color, 2)


def print_tracking_box_class(tracking_boxes):
    """TODO: Add a docstring!
    """
    for box_class in tracking_boxes:
        print(f'ID: {box_class.id} BOX: {box_class.box} SCORE: {box_class.score} DISTANCE: {box_class.distance}')
    print()

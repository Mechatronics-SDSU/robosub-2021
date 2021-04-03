"""
Inference System's tracking system for tracking a detected object.

Contributers:
Ian Reichard
Luka Jozic
"""

import cv2

from bounding_box import Box
from video_stream import VideoStream


def main():
    """Main function, currently runs meanshift"""
    vs = VideoStream()
    box = Box(0, 0, 640, 480)
    # meanshift(vs, box)
    return box


def meanshift(vs, box):
    """Perform meanshift algorithm between frames given the bounding box"""
    # Get the roi from bounding box
    frame_og = vs.read()
    frame = frame_og[box[1]:box[3], box[0]:box[2]]

    # Get HSV, Histogram of ROI
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist_roi = cv2.calcHist([hsv_roi], [0], None, [180], [0, 180])  # I still dont know what these args mean
    hist_roi = cv2.normalize(hist_roi, hist_roi, 0, 255, cv2.NORM_MINMAX)

    # Get HSV, Hist, Mask of whole frame
    hsv = cv2.cvtColor(frame_og, cv2.COLOR_BGR2HSV)
    mask = cv2.calcBackProject([hsv], [0], hist_roi, [0, 180], 1)

    # Perform Meanshift
    term_criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)
    _, result_box = cv2.meanShift(mask, (box[0], box[1], (box[2]-box[0]), (box[3]-box[1])), term_criteria)
    # cv2.rectangle(frame_og, (result_box[0], result_box[1]), (result_box[0]+result_box[2], result_box[1]+result_box[3]), (0, 255, 0), 2)
    print('result_box: ' + str(result_box))
    b = [result_box[0], result_box[1], (result_box[0]+result_box[2]), (result_box[1]+result_box[3])]
    return b

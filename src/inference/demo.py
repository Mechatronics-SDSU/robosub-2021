"""
Demo goes here!
"""

import cv2
from video_stream import VideoStream
from bounding_box import Box
import inference.inference as inf
import inference.tracking as track


def main(tracking='cell phone'):
    """
    Demo's entry point.
    Called if not imported.
    Warning to user if imported. Should never be imported by another module.
    """
    vs = VideoStream()  # Make our video stream object as part of demo
    bounding_box = []
    bounding_box = inf.main(vs, tracking, demo=True)  # Use TF model to return a bounding box of object
    print('Detected object, performing initial meanshift')
    bounding_box = track.meanshift(vs=vs, box=bounding_box)
    print('Bounding box obtained from 1st meanshift, looping now')
    while True:
        print(bounding_box)
        # Display box on original image
        frame = vs.read()
        cv2.rectangle(frame, (bounding_box[0], bounding_box[1]), (bounding_box[2], bounding_box[3]), (10, 255, 0), 2)
        cv2.imshow('DEMO', frame)
        cv2.waitKey(1)

        # Meanshift
        bounding_box = track.meanshift(vs=vs, box=bounding_box)


if __name__ != '__main__':
    print('WARN: Demo is being imported, recommended to run as main!')

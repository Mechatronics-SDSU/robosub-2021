"""
Demo goes here!
"""

import cv2
from video_stream import VideoStream
import inference.inference as inf
import inference.tracking as track


def main(tracking=['cell_phone']):
    """
    Demo's entry point.
    Called if not imported.
    Warning to user if imported. Should never be imported by another module.
    """

    vs = VideoStream()  # Make our video stream object as part of demo
    bounding_box = inf.main(vs, tracking)  # Use TF model to return a bounding box of object
    while True:
        bounding_box_tracked = track.main(bounding_box)
        # cv2.imshow()


if __name__ == '__main__':
    main()
else:
    print('WARN: Demo is being imported, recommended to run as main!')
    main()

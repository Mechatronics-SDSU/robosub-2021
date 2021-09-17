"""TODO: Add a docstring!
"""
import cv2
from threading import Thread


class VideoStream:
    """TODO: Add a docstring!
    """
    def __init__(self, resolution=(640, 480), framerate=30, input_stream=1):
        self.framerate = framerate
        self.stream = cv2.VideoCapture(input_stream)
        self.treading = True if input_stream == 1 else False
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.stream.set(3, resolution[0])
        self.stream.set(4, resolution[1])

        (self.grabbed, self.frame) = self.stream.read()  # Read first frame from the stream

        self.stopped = False  # Variable to control when the camera is stopped
        if self.treading:
            self.start()

    def get_frame_size(self):
        """
        :return: A tuple of the width and height of the current VideoCapture
        """
        width = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return width, height

    def start(self):
        """
        start the thread that reads frames from the video stream
        """
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        """
        keep looping indefinitely until the thread is stopped
        """
        while True:
            if self.stopped:
                self.stream.release()
                return

            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        """
        :return: most recent frame from thread if threading is enables else the current frame
        """
        if self.treading:
            return self.frame
        else:
            _, frame = self.stream.read()
            return frame

    def stop(self):
        """Mutator
        """
        self.stopped = True

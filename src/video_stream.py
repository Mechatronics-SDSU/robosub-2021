"""
Video Stream class with relevant methods and functions for getting video stream data

Contributers:
Ian Reichard
Luka Jozic
"""

# Python
import sys
import platform
from threading import Thread

# External
import cv2

# src
from bounding_box import Box


class VideoStream:
    """Camera object that controls video streaming from the Pi's camera"""

    def __init__(self, resolution=(1280, 720), fps=30, camera=0):
        """Initializes camera and the camera image stream

        Resolution is a tuple of width x and height y in the format (x,y)

        FPS is the number of frames per second on the video stream.

        Camera is -1 or 0 if there is only 1 camera installed.
        Having additional camera(s) means this needs to be modified to select a different camera.
        """
        self.width = resolution[0]
        self.height = resolution[1]

        # Force the video encoder based on system. Should only be V4L2 in production.
        self.encoder = 0
        if platform.system().lower() == 'windows':
            print('Found Windows Enviornment!')
            self.encoder = cv2.CAP_DSHOW
        elif platform.system().lower() == 'linux':
            print('Found Linux Enviornment!')
            self.encoder = cv2.CAP_V4L2
        else:
            print('Invalid Enviornment')
            sys.exit()
        self.stream = cv2.VideoCapture(camera, self.encoder)
        print('Stream initialized')

        # Setup video stream properties
        ret_val = ['Codec',
                   'Width',
                   'Height',
                   'FPS']
        ret = [self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')),
               self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0]),
               self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1]),

               self.stream.set(cv2.CAP_PROP_FPS, fps)]
        for i in range(len(ret)):
            if not ret[i]:
                print('Error initializing stream: Constructor arg \'' + ret_val[i] + '\' failed.')
        print('Stream setup finished.')

        # Read first frame from the stream
        (self.grabbed, self.frame) = self.stream.read()

        # Variable to control when the camera is stopped
        self.stopped = False

    def start(self):
        """Start the thread that reads frames from the video stream"""
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        """Keep looping indefinitely until the thread is stopped"""
        while True:
            # If the camera is stopped, stop the thread
            if self.stopped:
                # Close camera resources
                self.stream.release()
                return

            # Otherwise, grab the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        """Return the frame"""
        return self.frame

    def stop(self):
        """Indicate that the camera and thread should be stopped"""
        self.stopped = True

    def show(self):
        """Shows stream, should be for debugging only"""
        frame = self.read()
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # frame = cv2.resize(frame, (640, 480))
        cv2.imshow('img', frame)
        cv2.waitKey(1)

    def show_from_box(self, box):
        """Shows stream from bounding box"""
        while True:
            _, frame = self.stream.read()
            frame_copy = frame
            coords = box.get_coordinates()
            frame_copy = frame_copy[coords[1]:coords[3], coords[0]:coords[2]]
            cv2.imshow('img', frame_copy)
            if cv2.waitKey(1) == ord('q'):
                break

    def get_width(self):
        """Getter"""
        return self.width

    def get_height(self):
        """Getter"""
        return self.height


if __name__ == '__main__':
    print("Please import me!")
    sys.exit()
else:
    print("VideoStream class initialized!")

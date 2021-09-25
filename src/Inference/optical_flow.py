import cv2
import numpy as np


class OpticalFlow:
    def __init__(self, first_frame: list) -> None:
        self.first_frame = first_frame
        self.lk_params = dict(winSize=(25, 25),
                              maxLevel=4,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        self.old_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
        self.current_point = None
        self.old_points = np.array([[]], dtype=np.float32)
        self.new_points = [[0, 0]]


    def get_new_points(self, points: tuple, old_points: tuple) -> None:
        self.current_point, self.old_points = points, old_points

    def update_point(self, gray_frame: list) -> tuple:
        """
        :param gray_frame: Gray scale frame
        :return: Updated (x, y) coordinates of the tracking point
        """
        new_points, status, error = cv2.calcOpticalFlowPyrLK(self.old_gray, gray_frame, self.old_points, None,
                                                             **self.lk_params)
        self.old_gray = gray_frame.copy()
        self.old_points = new_points
        x, y = new_points.ravel()
        return int(x), int(y)





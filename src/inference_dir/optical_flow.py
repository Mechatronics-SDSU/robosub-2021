import cv2
import numpy as np

RADIUS = 5
WIDTH, HEIGHT = 50, 50


def rectangle_to_point(rectangle):
    xmin, xmax, ymin, ymax = rectangle
    x, y = (xmin + xmax) // 2, (ymin + ymax) // 2
    point = (x, y)
    old_points = np.array([[x, y]], dtype=np.float32)
    return point, old_points


class OpticalFlow:
    def __init__(self, first_frame):
        self.first_frame = first_frame
        self.lk_params = dict(winSize=(25, 25),
                              maxLevel=4,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        self.old_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
        self.current_point = None
        self.old_points = np.array([[]], dtype=np.float32)
        self.new_points = [[0, 0]]


    def get_new_points(self, rectangle):
        self.current_point, self.old_points = rectangle_to_point(rectangle)

    def update_point(self, gray_frame):
        new_points, status, error = cv2.calcOpticalFlowPyrLK(self.old_gray, gray_frame, self.old_points, None,
                                                             **self.lk_params)
        self.old_gray = gray_frame.copy()
        self.old_points = new_points
        x, y = new_points.ravel()
        return int(x), int(y)

    def draw(self, frame, x, y):
        cv2.circle(frame, (x, y), RADIUS, (0, 255, 0), -1)
        cv2.rectangle(frame, ((x - (RADIUS + WIDTH)), (y - (RADIUS + HEIGHT))),
                      ((x + (RADIUS + WIDTH)), (y + (RADIUS + HEIGHT))), 255, 3)

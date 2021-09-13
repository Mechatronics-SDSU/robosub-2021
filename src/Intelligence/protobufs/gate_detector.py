import cv2
import math
from src.utils.debug import (draw_lines,
                         draw_detected_tracking_boxes,
                         print_tracking_box_class)

BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)

MIN_VERT_LINE_DIFF = 50
MIN_CORNER_DISTANCE = 60
MIN_SLOPE = 45
MIN_OVERLAP_PERCENTAGE = 75


class TrackingBox:
    def __init__(self, id, box, score):
        self.id = [id]
        self.box = box
        self.score = [score]
        self.distance = self.__get_estimated_distance_to_gate()

    def __get_estimated_distance_to_gate(self):
        """
        :return: Estimated distance to the detected gate
        """
        gate_height = abs(self.box[3] - self.box[1])
        return round(1000 / gate_height, 2)


class GateDetector:

    def separate_lines(self, lines):
        """
        :param lines: A 2D array of lines of the format [x1, y1, x2, y2]
        :return: Two new 2D arrays with vertical and horizontal lines separated respectively
        """
        vertical = []
        horizontal = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            if width < MIN_SLOPE:
                if y2 - y1 < 0:
                    vertical.append([x2, y2, x1, y1])
                else:
                    vertical.append([x1, y1, x2, y2])
            elif height < MIN_SLOPE:
                if x2 - x1 < 0:
                    horizontal.append([x2, y2, x1, y1])
                else:
                    horizontal.append([x1, y1, x2, y2])
        return vertical, horizontal

    def find_both_posts(self, vertical):
        """
        :param vertical: 2D array of only vertical lines
        :return: The two most horizontally aligned vertical lines if found, else None
        """
        line1, line2, = None, None
        min_diff = MIN_VERT_LINE_DIFF
        for first_line in vertical:
            for second_line in vertical:
                first_line_x = (first_line[0] + first_line[2]) // 2  # mid x point of first line
                second_line_x = (second_line[0] + second_line[2]) // 2  # mid x point of second line
                horizontal_distance = abs(second_line_x - first_line_x)
                if horizontal_distance < 200:
                    continue

                line1_y1, line1_y2 = first_line[1], first_line[3]
                line2_y1, line2_y2 = second_line[1], second_line[3]
                # Diff between y1 and y2 for both lines added. The smaller the diff the more aligned
                diff = abs(line2_y1 - line1_y1) + abs(line2_y2 - line1_y2)
                if diff < min_diff:
                    line1, line2 = first_line, second_line
                    min_diff = diff

        return [line1, line2] if min_diff < MIN_VERT_LINE_DIFF else None

    def distance_between_points(self, x1, y1, x2, y2):
        """
        :return: Distance between the two given points
        """
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def find_corner_lines(self, vertical_lines, horizontal_lines, hor_x_idx, hor_y_idx):
        """
        Finds the best candidate lines that form a corner by comparing the distance between their closes points
        :param vertical_lines: 2D array of vertical lines
        :param horizontal_lines: 2D array of horizontal lines
        :param hor_x_idx: 0 or 1 which are the (x, y) indices of the leftmost point of a horizontal line
        :param hor_y_idx: 2 or 3 which are the (x, y) indices of the rightmost point of a horizontal line
        :return: An array of two lines and the distance between their closest points
        """
        min_vert, min_hor = None, None
        min_distance = float('inf')
        for vert_line in vertical_lines:
            for hor_line in horizontal_lines:
                x1, y1, x2, y2 = vert_line[0], vert_line[1], hor_line[hor_x_idx], hor_line[hor_y_idx]
                # Ensures that the left bar is to the left of the horizontal bar with a 5 pixel
                # margin and that the horizontal bar is above the vertical bar
                if hor_x_idx == 0 and x2 - x1 < -5 or y2 > y1:
                    continue
                # Ensures that the right bar is to the right of the horizontal bar with a -5 pixel
                # margin bar and that the horizontal bar is above the vertical bar
                if hor_y_idx == 2 and x2 - x1 > 5 or y2 > y1:
                    continue

                current_distance = self.distance_between_points(x1, y1, x2, y2)
                if current_distance < min_distance and current_distance < 50:
                    min_vert = vert_line
                    min_hor = hor_line
                    min_distance = current_distance

        return [min_vert, min_hor], min_distance

    def get_valid_gate_shape(self, left_corner, right_corner, left_diff, right_diff):
        """
        :param left_corner: 2D array with one vertical and one horizontal line that is the shape of a left corner
        :param right_corner: 2D array with one vertical and one horizontal line that is the shape of a right corner
        :param left_diff: The distance between the vertical and horizontal line of the left corner
        :param right_diff: The distance between the vertical and horizontal line of the right corner
        :return: The most valid gate shape from the given corners, from empty to full gate
        """
        if left_corner[0] is None and right_corner[0] is None:
            return [], -1
        elif left_corner[0] is None and right_corner[0]:
            return right_corner, 2
        elif right_corner[0] is None and left_corner[0]:
            return left_corner, 1

        if left_corner[0][0] >= right_corner[0][0] or \
                not self.horizontal_crossbar_aligned(left_corner[1], right_corner[1]):
            if left_diff < right_diff:
                return left_corner, 1
            else:
                return right_corner, 2

        return left_corner + right_corner, 4

    def horizontal_crossbar_aligned(self, left_crossbar, right_crossbar):
        """
        :param left_crossbar: An array representing the left horizontal line of a gate
        :param right_crossbar: An array representing the right horizontal line of a gate
        :return: True if the two crossbars have a difference <= 30 else False
        """
        line1_mid = (left_crossbar[1] + left_crossbar[3]) // 2
        line2_mid = (right_crossbar[1] + right_crossbar[3]) // 2
        diff = abs(line1_mid - line2_mid)
        return diff <= 30

    def get_box_overlap_percentage(self, box1, box2):
        """
        :param box1: A 2D array representing a tracking box (the bigger one)
        :param box2: A 2D array representing a tracking box (the smaller one)
        :return: The percentage of how many percent of box2 is overlapped by box1
        """
        XA1, YA1, XA2, YA2 = box1
        XB1, YB1, XB2, YB2 = box2

        area_of_intersection = max(0, min(XA2, XB2) - max(XA1, XB1)) * max(0, min(YA2, YB2) - max(YA1, YB1))
        area_a = (XA2 - XA1) * (YA2 - YA1)
        area_b = (XB2 - XB1) * (YB2 - YB1)
        overlap_percentage = area_of_intersection / min(area_a, area_b) * 100
        return overlap_percentage

    def group_lines_into_rectangles(self, src, lines):
        """
        :param src: The frame or image to draw on
        :param lines: A 2D array of horizontal lines
        """
        rectangles = []
        for line in lines:
            x1, y1, x2, y2 = line
            y1 -= 15
            y2 += 15
            cv2.rectangle(src, (x1, y1), (x2, y2), BLUE, 2)
            rectangles.append([x1, y1, x2, y2])

        grouped_rectangles = cv2.groupRectangles(rectangles, 1, 1.2)

        if len(grouped_rectangles[0]):
            x1, y1, x2, y2 = grouped_rectangles[0][0]
            cv2.rectangle(src, (x1, y1), (x2, y2), GREEN, 2)

    def get_box_coordinates(self, lines):
        """
        :param lines: Takes in a 2D array of lines
        :return: Coordinates representing a box
        """
        x1 = min(x[0] for x in lines) - 5
        y1 = min(y[1] for y in lines) - 10
        x2 = max(x[2] for x in lines) + 5
        y2 = max(y[3] for y in lines) + 10
        return x1, y1, x2, y2

    def get_boxes_ordered_by_size(self, box1, box2):
        """
        :param box1: A box object
        :param box2: Another box object
        :return: returns the boxes in order of size, largest first
        """
        box1_area = (max(box1.box[0], box1.box[2]) - min(box1.box[0], box1.box[2])) * \
                    (max(box1.box[1], box1.box[3]) - min(box1.box[1], box1.box[3]))

        box2_area = (max(box2.box[0], box2.box[2]) - min(box2.box[0], box2.box[2])) * \
                    (max(box2.box[1], box2.box[3]) - min(box2.box[1], box2.box[3]))

        return (box1, box2) if box1_area > box2_area else (box2, box1)

    def merge_similar_tracking_boxes(self, tracking_boxes):
        """
        Iterates over all the boxes and merges boxes that have enough overlap as they are considered the same box
        :param tracking_boxes: An array of tracking box objects
        :return: An updated array of tracking box objects
        """
        if len(tracking_boxes) > 1:
            for tracking_box in tracking_boxes:
                for other_tracking_box in tracking_boxes[1:]:
                    if tracking_box == other_tracking_box:
                        continue
                    larger_box, smaller_box = self.get_boxes_ordered_by_size(tracking_box, other_tracking_box)
                    overlap_percentage = self.get_box_overlap_percentage(larger_box.box, smaller_box.box)
                    if overlap_percentage > MIN_OVERLAP_PERCENTAGE:
                        larger_box.id += smaller_box.id
                        larger_box.score += smaller_box.score
                        tracking_boxes.remove(smaller_box)
        return tracking_boxes

    def create_tracking_box(self, lines, detection_id):
        """
        :param lines: A 2D array of lines
        :param detection_id: 1=left corner, 2=right_corner, 3=two posts, 4: two corners
        :return: A tracking object with the given attributes
        """
        detection_box = self.get_box_coordinates(lines)
        detection_score = self.get_detection_score(detection_id)
        tracking_box = TrackingBox(detection_id, detection_box, detection_score)
        return tracking_box

    def get_detection_score(self, detection_id):
        """
        :param detection_id: Integer between 1-4 representing the detection shape
        :return: The corresponding score to that detection shape
        """
        if detection_id == 3:
            return 30
        elif detection_id == 4:
            return 50
        return 10


    def detect(self, _frame):
        """
        Uses Fast Line Detector (FLD) to find lines that may form the shape of a gate
        :param frame: Current frame to perform detection on
        :return: An array of all the found tracking box objects
        """
        detected_tracking_boxes = []
        frame = cv2.medianBlur(_frame, 5)
        frame = cv2.resize(frame, (800, 400)) # Only for making testing of different videos easier

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Create default Fast Line Detector (FSD)
        fld = cv2.ximgproc.createFastLineDetector(_length_threshold=70,
                                                  _canny_th1=5,
                                                  _canny_th2=5,
                                                  _canny_aperture_size=3,
                                                  _do_merge=True)

        # Detect lines in the image
        lines = fld.detect(gray_frame)

        # Draw detected lines in the image
        drawn_img = fld.drawSegments(gray_frame, lines)

        if type(lines) is not type(None):
            vertical, horizontal = self.separate_lines(lines)

            posts = self.find_both_posts(vertical)

            left_corner_lines, left_corner_diff = self.find_corner_lines(vertical, horizontal, 0, 1)
            right_corner_lines, right_corner_diff = self.find_corner_lines(vertical, horizontal, 2, 3)

            corner_lines, shape_idx = self.get_valid_gate_shape(left_corner_lines,
                                                                right_corner_lines,
                                                                left_corner_diff,
                                                                right_corner_diff)

            if len(corner_lines):
                draw_lines(frame, corner_lines, BLUE)
                detected_tracking_boxes.append(self.create_tracking_box(corner_lines, shape_idx))

            if posts:
                draw_lines(frame, posts, BLUE)
                detected_tracking_boxes.append(self.create_tracking_box(posts, 3))

            detected_tracking_boxes = self.merge_similar_tracking_boxes(detected_tracking_boxes)
            draw_detected_tracking_boxes(frame, detected_tracking_boxes, RED)

        cv2.imshow("FLD", drawn_img)
        cv2.imshow("Frame", frame)
        return detected_tracking_boxes

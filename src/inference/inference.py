"""
Inference System Entry Point

Requires a Conda enviornment to install tflite.

Contributers:
Ian Reichard
Luka Jozic
"""

import cv2
import numpy as np
import os
import sys
import time
from threading import Thread
import importlib.util


class VideoStream:
    """Camera object that controls video streaming from the Picamera"""
    def __init__(self, resolution=(640, 480), framerate=10):
        # Initializes camera
        self.stream = cv2.VideoCapture(0)
        ret = self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        ret = self.stream.set(3, resolution[0])
        ret = self.stream.set(4, resolution[1])

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
        """Return the most recent frame"""
        return self.frame

    def stop(self):
        """Indicate that the camera and thread should be stopped"""
        self.stopped = True


def main():
    """Main function"""
    # print("Hello from ian_dev branch!")
    webcam_detection()


def webcam_detection():
    """Modifying Luka's webcam detection code a bit and putting it here"""

    # Placing these here so we don't have to pass args each time we run file.
    model_dir = 'model'
    model_graph = 'detect.tflite'
    model_labels = 'labelmap.txt'
    model_thresh = float(0.2)
    camera_resolution = '1280x720'
    use_tpu = 'store_true'
    res_width, res_height = camera_resolution.split('x')
    img_width, img_height = int(res_width), int(res_height)

    # Import the right tflite TPU package
    if importlib.util.find_spec('tflite_runtime'):
        from tflite_runtime.interpreter import Interpreter
        if use_tpu:
            from tflite_runtime.interpreter import load_delegate
    else:
        print('No tflite runtime!')
        sys.exit()

    # Assign filename for using Edge TPU model
    if use_tpu:
        if model_graph == 'detect.tflite':
            model_graph = 'detect.tflite'

    # Get directory of graphs/labels
    os_cwd = os.getcwd()
    path_graph = os.path.join(os_cwd, model_dir, model_graph)
    path_labels = os.path.join(os_cwd, model_dir, model_labels)

    # Open and load the label map
    with open(path_labels, 'r') as f:
        labels = [line.strip() for line in f.readlines()]

    # Starter model has a strange ??? that needs to be removed, not sure why.
    if labels[0] == '???':
        del (labels[0])

    # Load model
    if use_tpu:
        interpreter = Interpreter(model_path=path_graph)
        # experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
    else:
        interpreter = Interpreter(model_path=path_graph)
    print('Loaded model at ' + path_graph)
    interpreter.allocate_tensors()

    # Get the model's details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    height = input_details[0]['shape'][1]
    width = input_details[0]['shape'][2]
    floating_model = (input_details[0]['dtype'] == np.float32)

    # Used to normalize pixel values on floating models
    input_mean = 127.5
    input_std = 127.5

    # FPS calculation
    fps_calc = 1  # Set to 1 for first frame, just to have something
    freq = cv2.getTickFrequency()

    # Get video stream using VideoStream class
    videostream = VideoStream(resolution=(img_width, img_height), framerate=30).start()  # Maybe change this framerate call?
    time.sleep(1)
    term_criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)

    # Tracking box bounds
    object_tracking, y_min, y_max, x_min, x_max = '', 0, 0, 0, 0

    # Time in seconds to wait until tflite model is run again. This will run meanshift in the meantime.
    tf_swap_delay = 2

    # Timers
    timer_tf_t1 = cv2.getTickCount()
    timer_tf_t2 = 0

    while True:
        # Calculate FPS delta by measuring time 1 at start of while loop
        timer_fps_t1 = cv2.getTickCount()

        # Get frames from video stream
        frame_original = videostream.read()

        # Resize
        frame = frame_original.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (width, height))
        input_data = np.expand_dims(frame_resized, axis=0)

        # Normalize
        if floating_model:
            input_data = (np.float32(input_data) - input_mean) / input_std

        # Swap from meanshift to tflite detection if tf_swap_delay has elapsed
        if (timer_tf_t2 - timer_tf_t1) / freq > tf_swap_delay:
            timer_tf_t1 = cv2.getTickCount()
            print('Time: ', (timer_tf_t2 - timer_tf_t1)/freq)

            # Perform tflite object detection
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()

            # Retrieve detection results
            boxes = interpreter.get_tensor(output_details[0]['index'])[
                0]  # Bounding box coordinates of detected objects
            classes = interpreter.get_tensor(output_details[1]['index'])[0]  # Class index of detected objects
            scores = interpreter.get_tensor(output_details[2]['index'])[0]  # Confidence of detected objects
            print('Classes: ' + str(len(classes)))
            print('Labels: ' + str(len(labels)))
            # num = interpreter.get_tensor(output_details[3]['index'])[0]  # Total number of detected objects (inaccurate and not needed)

            # Loop over all detections and draw detection box if confidence is above minimum threshold
            for i in range(len(scores)):
                if (scores[i] > model_thresh) and (scores[i] <= 1.0):
                    # Get bounding box coordinates and draw box
                    # Interpreter can return coordinates that are outside of image dimensions, need to force them to be within image using max() and min()
                    ymin = int(max(1, (boxes[i][0] * img_height)))
                    xmin = int(max(1, (boxes[i][1] * img_width)))
                    ymax = int(min(img_height, (boxes[i][2] * img_height)))
                    xmax = int(min(img_width, (boxes[i][3] * img_width)))
                    # print((xmin, ymin), ", ", (xmax, ymax))

                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (10, 255, 0), 2)

                    # Draw label
                    object_name = labels[int(classes[i])]  # Look up object name from "labels" array using class index
                    label = '%s: %d%%' % (object_name, int(scores[i] * 100))  # Example: 'person: 72%'
                    labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)  # Get font size
                    label_ymin = max(ymin, labelSize[1] + 10)  # Make sure not to draw label too close to top of window
                    cv2.rectangle(frame, (xmin, label_ymin - labelSize[1] - 10),
                                  (xmin + labelSize[0], label_ymin + baseLine - 10), (255, 255, 255),
                                  cv2.FILLED)  # Draw white box to put label text in
                    cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0),
                                2)  # Draw label text
                    if object_name == 'cell phone':
                        object_to_track = 'cell phone'
                        x_min, y_min, x_max, y_max = xmin, ymin, xmax, ymax

        # Perform Mean Shift in the 'in between' frames where we aren't doing tflite
        # TODO change from cell phone specifically to other objects? -Ian
        if object_tracking == 'cell phone':
            roi = frame[y_min:y_max, x_min:x_max]
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            roi_hist = cv2.calcHist([hsv_roi], [0], None, [180], [0, 180])  # I don't know what these values are for. Luka pls comment.
            roi_hist = cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.calcBackProject([hsv], [0], roi_hist, [0, 180], 1)

            # Mean shift and get new tracking rectangle
            _, track_window = cv2.meanShift(mask, (x_min, y_min, x_max-x_min, y_max-y_min), term_criteria)
            x, y, w, h = track_window
            # Draw green rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Draw FPS
        cv2.putText(frame, 'FPS: {0:.2f}'.format(fps_calc), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)
        # Display Frame
        cv2.imshow('Object detector', frame)

        # Calculate framerate after everything is done this loop
        timer_tf_t2, timer_fps_t2 = cv2.getTickCount(), cv2.getTickCount()
        time_fps = (timer_fps_t2 - timer_fps_t1) / freq
        fps_calc = 1 / time_fps

        # 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break


if __name__ == '__main__':
    main()
else:
    print('Inference is being imported, should only be used for testing!')
    main()

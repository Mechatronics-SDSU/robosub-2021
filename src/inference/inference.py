"""
Inference System's model code for initial object detection.

Requires a Conda enviornment to install tflite.

Contributers:
Ian Reichard
Luka Jozic
"""

# Python
import os
import sys
import time
import importlib.util

# External
import cv2
import numpy as np

# src
from video_stream import VideoStream
from bounding_box import Box


def main(vs, tracking):
    """Main function"""
    webcam_detection(vs, tracking)


def webcam_detection(vs, tracking='cell_phone'):
    """Modifying Luka's webcam detection code a bit and putting it here"""

    # Placing these here so we don't have to pass args each time we run file.
    model_dir = 'inference\\model'
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
            pass
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
    # videostream = VideoStream(resolution=(img_width, img_height)).start()  # Maybe change this framerate call?
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
        vs.start()
        frame_original = vs.read()

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

            # Perform tflite object detection
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()

            # Retrieve detection results
            boxes = interpreter.get_tensor(output_details[0]['index'])[
                0]  # Bounding box coordinates of detected objects
            classes = interpreter.get_tensor(output_details[1]['index'])[0]  # Class index of detected objects
            scores = interpreter.get_tensor(output_details[2]['index'])[0]  # Confidence of detected objects
            # print('Classes: ' + str(len(classes)))
            # print('Labels: ' + str(len(labels)))
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
                    labelsize, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)  # Get font size
                    label_ymin = max(ymin, labelsize[1] + 10)  # Make sure not to draw label too close to top of window
                    cv2.rectangle(frame, (xmin, label_ymin - labelsize[1] - 10),
                                  (xmin + labelsize[0], label_ymin + baseline - 10), (255, 255, 255),
                                  cv2.FILLED)  # Draw white box to put label text in
                    cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0),
                                2)  # Draw label text
                    if object_name == tracking[0]:
                        object_to_track = tracking[0]
                        x_min, y_min, x_max, y_max = xmin, ymin, xmax, ymax
        # 3/30/2021 Refactor: Meanshift no longer in this file -IAR
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
    return Box(vs.get_width, vs.get_height, x_min, y_max)


if __name__ != '__main__':
    main(vs=VideoStream(), tracking='cell_phone')
else:
    print('Import me!')
    sys.exit()

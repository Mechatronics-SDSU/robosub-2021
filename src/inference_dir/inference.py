import importlib.util
from tflite_runtime.interpreter import Interpreter
import os
import numpy as np
import cv2


MODEL_NAME = 'model'
GRAPH_NAME = 'detect.tflite'
LABELMAP_NAME = 'labelmap.txt'
min_conf_threshold = 0.5


# Import TensorFlow libraries
importlib.util.find_spec('tflite_runtime')

# Get path to current working directory
CWD_PATH = os.getcwd()

# Path to .tflite file, which contains the model that is used for object detection
PATH_TO_CKPT = os.path.join(CWD_PATH, MODEL_NAME, GRAPH_NAME)

# Path to label map file
PATH_TO_LABELS = os.path.join(CWD_PATH, MODEL_NAME, LABELMAP_NAME)

# Load the label map
with open(PATH_TO_LABELS, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Have to do a weird fix for label map if using the COCO "starter model" from
# https://www.tensorflow.org/lite/models/object_detection/overview
# First label is '???', which has to be removed.
if labels[0] == '???':
    del (labels[0])


input_mean = 127.5
input_std = 127.5

resW, resH = '1280x720'.split('x')
imW, imH = int(resW), int(resH)


class Object_Detector:
    def __init__(self):
        self.interpreter = Interpreter(model_path=PATH_TO_CKPT)
        self.interpreter.allocate_tensors()
        self.get_model_details()

    def get_model_details(self):
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.height = self.input_details[0]['shape'][1]
        self.width = self.input_details[0]['shape'][2]
        self.floating_model = (self.input_details[0]['dtype'] == np.float32)

    async def detect(self, frame, object_to_detect):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (self.width, self.height))
        input_data = np.expand_dims(frame_resized, axis=0)

        # Normalize pixel values if using a floating model (i.e. if model is non-quantized)
        if self.floating_model:
            input_data = (np.float32(input_data) - input_mean) / input_std

        # Perform the actual detection by running the model with the image as input
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # Retrieve detection results
        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]  # Bounding box coordinates of detected objects
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]  # Class index of detected objects
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]  # Confidence of detected objects

        if ((scores[0] > min_conf_threshold) and (scores[0] <= 1.0)):
            # Get bounding box coordinates and store coordinates
            # Interpreter can return coordinates that are outside of image dimensions, need to force them to be within
            # image using max() and min()
            ymin = int(max(1, (boxes[0][0] * imH)))
            xmin = int(max(1, (boxes[0][1] * imW)))
            ymax = int(min(imH, (boxes[0][2] * imH)))
            xmax = int(min(imW, (boxes[0][3] * imW)))

            object_name = labels[int(classes[0])]  # Look up object name from "labels" array using class index
            if object_name == object_to_detect:
                return (xmin, xmax, ymin, ymax)
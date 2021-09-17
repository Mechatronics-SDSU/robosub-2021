import importlib.util
from tflite_runtime.interpreter import Interpreter
import os
import numpy as np
import cv2
from utils.consants import (GRAPH_NAME, LABELMAP_NAME, MIN_CONF_THRESHOLD)

importlib.util.find_spec('tflite_runtime')  # Import TensorFlow libraries

CWD_PATH = os.getcwd() # Get path to current working directory

input_mean = 127.5
input_std = 127.5


class ObjectDetector:
    def __init__(self, model_name, frame_size):
        self.interpreter = Interpreter(model_path=os.path.join(CWD_PATH, 'Inference', model_name, GRAPH_NAME))
        self.interpreter.allocate_tensors()
        self.setup_model()
        self.labels = self.load_label_map(model_name)
        self.frame_width, self.frame_height = frame_size

    def load_label_map(self, model_name):
        """
        :param model_name: Name of the directory where the model files are stored
        :return: A list of all the object the model can detect
        """
        PATH_TO_LABELS = os.path.join(CWD_PATH, 'Inference', model_name, LABELMAP_NAME)
        with open(PATH_TO_LABELS, 'r') as f:
            labels = [line.strip() for line in f.readlines()]

        if labels[0] == '???':
            del (labels[0])

        return labels

    def setup_model(self):
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.height = self.input_details[0]['shape'][1]
        self.width = self.input_details[0]['shape'][2]
        self.floating_model = (self.input_details[0]['dtype'] == np.float32)

    async def detect(self, frame, objects_to_detect):
        """
        :param frame: Frame to perform detection on
        :param object_to_detect: Single object o detect
        :return: Bounding box of object if detected else None
        """
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

        detected_bounding_boxes = {}
        for i in range(len(scores)):
            if ((scores[i] > MIN_CONF_THRESHOLD) and (scores[i] <= 1.0)):
                # Get bounding box coordinates and store coordinates
                # Interpreter can return coordinates that are outside of image dimensions, need to force them to be within
                # image using max() and min()
                ymin = int(max(1, (boxes[i][0] * self.frame_height)))
                xmin = int(max(1, (boxes[i][1] * self.frame_width)))
                ymax = int(min(self.frame_height, (boxes[i][2] * self.frame_height)))
                xmax = int(min(self.frame_width, (boxes[i][3] * self.frame_width)))

                object_name = self.labels[int(classes[i])]  # Look up object name from "labels" array using class index
                if object_name in objects_to_detect:
                    detected_bounding_boxes[(xmin, ymin, xmax, ymax)] = [object_name, int(scores[i] * 100)]

        return detected_bounding_boxes
import cv2
from inference_dir.gate_detector import GateDetector
import pickle

gate_detector = GateDetector()
cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')


while True:
	_, _frame = cap.read()
	result = gate_detector.detect(_frame)
	if result != None:
    		val = pickle.dumps(result)
	cv2.imshow("Frame", _frame)
    

import cv2
from inference_dir.gate_detector import GateDetector

cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')
gate_detector = GateDetector()

while True:
    _, _frame = cap.read()
    result = gate_detector.detect(_frame)

    key = cv2.waitKey(30)
    if key == 27:
        break

cv2.destroyAllWindows()
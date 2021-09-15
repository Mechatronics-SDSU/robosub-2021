import cv2
import numpy as np

cap = cv2.VideoCapture('Additional_Test_Video.mp4')

# (x, y, w, h) = cv2.boundingRect(c)
# cv2.rectangle(frame, (x,y), (x+w, y+h), (0, 255, 0), 20)
# roi = frame[y:y+h, x:x+w]

count = 0
while True:
    count +=1
    ret, frame = cap.read()
    # (height, width) = frame.shape[:2]
    sky = frame[115:581, 18:644]
    # cv2.imshow('Video', sky)
    print(f" [Writing Image ... {count:04d} ", end='\r')
    cv2.imwrite(f"build/test_capture_{count:05d}.png", sky)

    if cv2.waitKey(1) == 27:
        exit(0)
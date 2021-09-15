"""Simple test script written to verify the Test Video is not a broken file.
"""
import cv2

input_video_path = 'Additional_Test_Video.mp4'
cap = cv2.VideoCapture(input_video_path)

while cap.isOpened():  # Check file path integrity
    ret, frame = cap.read()
    print(frame, ret)
    if ret:
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
    else:
        break

cap.release()
cv2.destroyAllWindows()

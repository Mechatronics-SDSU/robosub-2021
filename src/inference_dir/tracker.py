import cv2
import time
from threading import Thread
import asyncio
from utils.video_stream import VideoStream
from optical_flow import OpticalFlow
from inference_dir.inference import Object_Detector

resW, resH = '1280x720'.split('x')
imW, imH = int(resW), int(resH)


# Initialize video stream
videostream = VideoStream(resolution=(imW, imH), framerate=30).start()
time.sleep(1)
first_frame = videostream.read()


ob = Object_Detector()
optical_flow = OpticalFlow(first_frame=first_frame)


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

new_loop = asyncio.new_event_loop()
t = Thread(target=start_loop, args=(new_loop,))
t.start()

point = asyncio.run_coroutine_threadsafe(ob.detect(first_frame, 'remote'), new_loop)


# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()
while True:
    # Start timer (for calculating frame rate)
    fps_timer_start = cv2.getTickCount()

    # Grab frame from video stream
    frame1 = videostream.read()
    frame = frame1.copy()
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    if point.done():
        result = point.result()
        if result:
            rect = result
            print("RECT: ", rect)
            print("NEW POINT: ", optical_flow.new_points)
            if not (rect[0] <= optical_flow.new_points[0][0] <= rect[1] and
                    rect[2] <= optical_flow.new_points[0][1] <= rect[3]):

                optical_flow.get_new_points(rect)
                print("NEW POINT: ", optical_flow.current_point, "====================================")
                w, h = rect[1] - rect[0], rect[3] - rect[2]

        timer_start = time.time()
        point = asyncio.run_coroutine_threadsafe(ob.detect(frame, 'remote'), new_loop)

    if optical_flow.current_point != None:
        x, y = optical_flow.update_point(gray_frame)
        optical_flow.draw(frame, x, y)



    # Draw framerate in corner of frame
    cv2.putText(frame, 'FPS: {0:.2f}'.format(frame_rate_calc), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)
    # All the results have been drawn on the frame, so it's time to display it.
    cv2.imshow('Object detector', frame)


    # Calculate framerate
    fps_timer_end = cv2.getTickCount()
    fps_time = (fps_timer_end - fps_timer_start) / freq
    frame_rate_calc = 1 / fps_time

    if cv2.waitKey(1) == ord('q'):
        break

# Clean up
cv2.destroyAllWindows()
videostream.stop()

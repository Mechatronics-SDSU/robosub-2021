import cv2
import time
from threading import Thread
import asyncio
from utils.video_stream import VideoStream
from Inference.object_detector import ObjectDetector
from Inference.gate_detector import GateDetector

from utils.consants import WIN_WIDTH, WIN_HEIGHT, GREEN, WAIT_KEY, BLUE
from utils.utils import (point_to_rectangle, rectangle_to_point, draw_point, draw_detected_object,
                         DetectedObject, FPS, draw_text,update_optical_flow_list)


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class Inference:
    """
    Inference class to invoke other object detection classes and call their functions. Uses a VideoStream object to
    process frames and a GateDetector or ObjectDetector to perform detections and send them back to intelligence.
    """
    def __init__(self, input_stream):
        self.videostream = VideoStream(resolution=(WIN_WIDTH, WIN_HEIGHT), input_stream=input_stream)
        time.sleep(1)

    def run_gate_detector(self) -> None:
        """
        run gate detector in while loop and feed detections back to intelligence
        """
        gate_detector = GateDetector()
        fps = FPS().start()
        while True:
            fps.update()
            frame = self.videostream.read()
            detected_objects = gate_detector.detect(frame) #TODO: Send back DetectedObject class
            for detected_object in detected_objects:
                print(detected_object)
                draw_detected_object(frame, detected_object, GREEN)
                # TODO: Send back detected_object to intelligence here

            fps.stop()
            draw_text(frame, f'FPS: {round(fps.fps(), 2)}', (30, 50), BLUE)

            cv2.imshow('Frame', frame)
            if cv2.waitKey(WAIT_KEY) == ord('q'):
                break

        cv2.destroyAllWindows()


    def run_object_detection(self, model_name: str, objects: list, tracking=True) -> None:
        """
        run object detector in while loop and feed detections back to intelligence
        """
        first_frame = self.videostream.read()

        object_detector = ObjectDetector(model_name=model_name, frame_size=self.videostream.get_frame_size())

        event_loop = asyncio.new_event_loop()
        detection_thread = Thread(target=start_loop, args=(event_loop,))
        detection_thread.start()
        detection = asyncio.run_coroutine_threadsafe(object_detector.detect(first_frame, objects), event_loop)

        optical_flow = []
        results, object_name, bounding_box = None, None, None
        fps = FPS().start()
        while True:
            frame1 = self.videostream.read()
            try:
                frame = frame1.copy()
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                fps.update()
                if tracking:
                    if detection.done():
                        results = detection.result()
                        update_optical_flow_list(optical_flow, len(results), frame)

                        for i, rect in enumerate(results.keys()): # Convert detection box to point and get new points
                            point, old_points = rectangle_to_point(rect)
                            optical_flow[i].get_new_points(point, old_points)
                        # Start the next detection coroutine concurrently
                        detection = asyncio.run_coroutine_threadsafe(object_detector.detect(frame, objects), event_loop)

                    if results: # Loop over all results and update their position and feed data to intelligence
                        for i, rect in enumerate(results.keys()):
                            if optical_flow[i].current_point != None:
                                x, y = optical_flow[i].update_point(gray_frame)
                                w, h = rect[2] - rect[0], rect[3] - rect[1]
                                draw_point(frame, x, y)
                                x1, y1, x2, y2 = point_to_rectangle(x, y, w, h)
                                bounding_box = (x1, y1, x2, y2)
                                object_name = results[rect][0]
                                score = results[rect][1]
                                detected_object = DetectedObject(object_name, bounding_box, score)
                                draw_detected_object(frame, detected_object, GREEN)
                                # TODO: Send back detected_object to intelligence here

                else: # If tracking is not activate, only perform detections i.e. no tracking (lower FPS)
                    detection = asyncio.run_coroutine_threadsafe(object_detector.detect(frame, objects), event_loop)
                    results = detection.result()
                    for bounding_box in results.keys():
                        object_name = results[bounding_box][0]
                        score = results[bounding_box][1]
                        detected_object = DetectedObject(object_name, bounding_box, score)
                        draw_detected_object(frame, detected_object, GREEN)
                        # TODO: Send back detected_object to intelligence here

                fps.stop()
                draw_text(frame, f'FPS: {round(fps.fps(), 2)}', (30, 50), BLUE)

                cv2.imshow('Frame', frame)
            except Exception as e:
                print("Error: ", e)
            finally:
                if cv2.waitKey(WAIT_KEY) == ord('q'):
                    break

        event_loop.stop()
        self.videostream.stop()
        cv2.destroyAllWindows()




import cv2
import time
from threading import Thread
import asyncio
from utils.video_stream import VideoStream
from inference_dir.optical_flow import OpticalFlow
from inference_dir.object_detector import ObjectDetector
from inference_dir.gate_detector import GateDetector

from utils.consants import WIN_WIDTH, WIN_HEIGHT, GREEN
from utils.utils import (point_to_rectangle, rectangle_to_point, draw_point, draw_detected_object,
                         DetectedObject, FPS)





def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class Inference:
    def __init__(self, input_stream):
        self.videostream = VideoStream(resolution=(WIN_WIDTH, WIN_HEIGHT), input_stream=input_stream)
        time.sleep(1)

    def run_gate_detector(self):
        """
        run gate detector in while loop and feed detections back to intelligence
        """
        gate_detector = GateDetector()
        fps = FPS().start()
        while True:
            fps.update()
            frame = self.videostream.read()
            detected_objects = gate_detector.detect(frame)
            for detected_object in detected_objects:
                draw_detected_object(frame, detected_object, GREEN)
                # TODO: Send back detected_object to intelligence here

            fps.stop()
            fps.display_fps(frame, fps.fps())

            cv2.imshow('Frame', frame)
            if cv2.waitKey(30) == ord('q'):
                break

        cv2.destroyAllWindows()


    def run_object_detection(self, model_name, objects, tracking=True):
        """
       run object detector in while loop and feed detections back to intelligence
       """
        first_frame = self.videostream.read()

        ob = ObjectDetector(model_name=model_name, frame_size=self.videostream.get_frame_size())

        new_loop = asyncio.new_event_loop()
        t = Thread(target=start_loop, args=(new_loop,))
        t.start()
        detection = asyncio.run_coroutine_threadsafe(ob.detect(first_frame, objects), new_loop)

        optical_flow = []
        results, object_id, bounding_box = None, None, None
        fps = FPS().start()
        while True:
            frame1 = self.videostream.read()
            frame = frame1.copy()
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fps.update()
            if tracking:
                if detection.done():
                    results = detection.result()
                    self.update_optical_flow_list(optical_flow, len(results), frame)

                    for i, rect in enumerate(results.keys()): # Convert detection box to point and get new points
                        point, old_points = rectangle_to_point(rect)
                        optical_flow[i].get_new_points(point, old_points)
                    # Start the next detection coroutine concurrently
                    detection = asyncio.run_coroutine_threadsafe(ob.detect(frame, objects), new_loop)

                if results: # Loop over all results and update their position and feed data to intelligence
                    for i, rect in enumerate(results.keys()):
                        if optical_flow[i].current_point != None:
                            x, y = optical_flow[i].update_point(gray_frame)
                            w, h = rect[2] - rect[0], rect[3] - rect[1]
                            draw_point(frame, x, y)
                            x1, y1, x2, y2 = point_to_rectangle(x, y, w, h)
                            bounding_box = (x1, y1, x2, y2)
                            object_id = results[rect][0]
                            score = results[rect][1]
                            detected_object = DetectedObject(object_id, bounding_box, score)
                            draw_detected_object(frame, detected_object, GREEN)
                            # TODO: Send back detected_object to intelligence here

            else: # If tracking is not activate, only perform detections i.e. no tracking (lower FPS)
                detection = asyncio.run_coroutine_threadsafe(ob.detect(frame, objects), new_loop)
                results = detection.result()
                for bounding_box in results.keys():
                    object_id = results[bounding_box][0]
                    score = results[bounding_box][1]
                    detected_object = DetectedObject(object_id, bounding_box, score)
                    draw_detected_object(frame, detected_object, GREEN)
                    # TODO: Send back detected_object to intelligence here

            fps.stop()
            fps.display_fps(frame, fps.fps())

            cv2.imshow('Frame', frame)
            if cv2.waitKey(1) == ord('q'):
                break

        cv2.destroyAllWindows()
        self.videostream.stop()

    def update_optical_flow_list(self, optical_flow_list, num_results, frame):
        """
        :param optical_flow_list: Array of OpticalFlow instances currently used for tracking
        :param num_results: number of most recent results from the object detection
        :param frame: most recent frame used as initializer frame for new OpticalFlow instance
        """
        if len(optical_flow_list) > num_results:
            while len(optical_flow_list) != num_results:
                del optical_flow_list[-1]

        if len(optical_flow_list) < num_results:
            while len(optical_flow_list) != num_results:
                optical_flow_list.append(OpticalFlow(first_frame=frame))


















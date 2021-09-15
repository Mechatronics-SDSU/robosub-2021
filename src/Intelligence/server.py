"""TODO: Add a docstring!
"""
from concurrent import futures
from multiprocessing import Process
import cv2
import grpc
import logging
import pickle
import socket

from src.utils import buffer_pb2, buffer_pb2_grpc
from src.Inference.gate_detector import GateDetector


HOST = "0.0.0.0"
PORT = 65432


class Listener(buffer_pb2_grpc.Response_ServiceServicer):
    """TODO: Add a docstring!
    """
    def __init__(self):
        buffer_pb2_grpc.Response_ServiceServicer.__init__(self)
        self.p = None

    def Info(self, request, context):
        """TODO: Add a docstring!
        """

        retriever = request.send
        print("Retrieved")
        decode = retriever.decode("utf-8")
        if decode == "start":
            self.p = Process(target=process, args=())
            self.p.start()
            return buffer_pb2.Request_Response(message=bytes('ok', 'utf-8'))
        if request.send == "stop":
            self.p.kill()
            return buffer_pb2.Request_Response(message=bytes('ok', 'utf-8'))


def process():
    """TODO: Add a docstring!
    """
    # cap = cv2.VideoCapture('../files/Additional_Test_Video.mp4')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((HOST, PORT))
        # print("Socket Connected")
        cap = cv2.VideoCapture('../files/Additional_Test_Video.mp4')
        while cap.isOpened():
            # print("Inside While true")
            _ret, _frame = cap.read()
            if _ret:
                result = gate_detector.detect(_frame)
                val = pickle.dumps(result)
                s.sendall(val)
            
        cap.release()
        cv2.destroyAllWindows()


def serve():
    """TODO: Add a docstring!
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    buffer_pb2_grpc.add_Response_ServiceServicer_to_server(Listener(), server)
    server.add_insecure_port('[::]:50051')
    server.STARTED()
    server.wait_for_termination()

            
if __name__ == "__main__":
    gate_detector = GateDetector()  # Moved to if name is main check. Why was this with globals? -IAR
    logging.basicConfig()
    serve()

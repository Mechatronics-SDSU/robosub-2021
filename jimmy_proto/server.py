from concurrent import futures
import grpc
import buffer_pb2
import buffer_pb2_grpc
import time
import threading
import logging
import pickle
import os
import cv2
from inference_dir.gate_detector import GateDetector
from multiprocessing import Process
import socket
import docker
CLIENT = docker.from_env()


HOST = '127.0.0.1'
PORT = 65432


SERVER_ADDRESS = "localhost:23333"


gate_detector = GateDetector()
cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')


class Listener(buffer_pb2_grpc.Response_ServiceServicer):
	def __init__(self):
		buffer_pb2_grpc.Response_ServiceServicer.__init__(self)
		self.p = None
		containers_list = CLIENT.containers.list(all=True)
		if not containers_list != "server":
			self.container = False
		else:
			self.container = True


	def Info(self, request, context):
		if self.container == True:
			containers_list = CLIENT.containers.list(all=True)
			for cont in containers_list:
			   	cont.remove(force=True)
			   	self.container = False
		elif self.container == False:
			CLIENT.containers.run(name="server", command=None, image="ubuntu", detach=True)
		retriever = request.send
		decode = retriever.decode("utf-8")
		if  decode == "start":
			self.p = Process(target=process, args=(cap,))
			self.p.start()
			return buffer_pb2.Request_Response(message = bytes('ok', 'utf-8'))
		if request.send == "stop":
			self.p.kill()
			return buffer_pb2.Request_Response(message = bytes('ok', 'utf-8'))


def process(cap,):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			s.connect((HOST,PORT))
			while True:
				_, _frame = cap.read()
				result = gate_detector.detect(_frame)
				val = pickle.dumps(result)
				s.sendall(val)
		
			
def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	buffer_pb2_grpc.add_Response_ServiceServicer_to_server(Listener(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination()

			
if __name__ == "__main__":
	logging.basicConfig()
	serve()

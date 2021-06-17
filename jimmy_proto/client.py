import os
import buffer_pb2
import buffer_pb2_grpc
import time
import grpc
import logging
import cv2
import pickle
from inference_dir.gate_detector import GateDetector
import server
from multiprocessing import Process
import docker
import socket
CLIENT = docker.from_env()


HOST = '127.0.0.1'
PORT = 65432


SERVER_ADDRESS = "localhost:23333"


CLIENT_ID = 1
start = False


gate_detector = GateDetector()
cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')
tracking = {}


def run():
	channel = grpc.insecure_channel('localhost:50051')
	stub = buffer_pb2_grpc.Response_ServiceStub(channel)
	#try:
	response_string = b"start"
	stub.Info(buffer_pb2.Send_Request(send=response_string))
		#response = self.stub.Info(buffer_pb2.Send_Request(req=b(request)))
	term_socket()
			
	#except Exception as e:
		#print('waiting for server to connect...')
		#print(e)
	time.sleep(1)


def term_socket():
	#val = pickle.dumps(thisdict)
	#stub.Info(response.message)
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((HOST, PORT))
		s.listen(5)
		conn, addr = s.accept()
		while True:
			data = conn.recvfrom(1024)[0]
			print(data)
		conn.close()
			
			
def stop():
	server.check(p, "stop")
				
   
if __name__ == '__main__':
	logging.basicConfig()
	run()

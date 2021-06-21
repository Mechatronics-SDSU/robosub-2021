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
<<<<<<< HEAD
	with grpc.insecure_channel('localhost:50051') as channel:
		try:
			stub = buffer_pb2_grpc.Response_ServiceStub(channel)
			i = 0
			p = Process(target=process, args=(cap,stub,i,))
			server.check(p, "start")
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> e8e9bb062db83045f3c34e9dad6a29b74876edf4
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.connect((HOST, PORT))
				print("Inside")
				data = s.recv(1024)
<<<<<<< HEAD
=======
			print("Is p alive? ", p.is_alive())
			if False:
				server.check(p, "kill")
>>>>>>> c858c832581ee3aa8e15f8d7064e905f4c22ae77
=======
>>>>>>> e8e9bb062db83045f3c34e9dad6a29b74876edf4
		except:
			print('waiting for server to connect...')
			time.sleep(1)


def process(cap,stub,i):
	while True:
		_, _frame = cap.read()
		result = gate_detector.detect(_frame)
		if result != None:
			i += 1
			val = pickle.dumps(result)
			response = stub.Info(buffer_pb2.Send_Request(send=val))
			tracking[i] = response.message
			print(response.message)
=======
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
>>>>>>> 376fe75a535040e3e1d710870debc8aa02a2206a


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

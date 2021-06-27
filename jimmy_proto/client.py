import os
import buffer_pb2
import buffer_pb2_grpc
import time
import grpc
import logging
import cv2
import pickle
from inference_dir.gate_detector import GateDetector
from multiprocessing import Process
import docker
import socket
import subprocess
CLIENT = docker.from_env()


HOST = '127.0.0.1'
PORT = 65432


SERVER_ADDRESS = "localhost:23333"


CLIENT_ID = 1
start = False


gate_detector = GateDetector()
cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')
tracking = {}

class Spawn():
	def __init__(self):	
		self.run()
		
		
	def run(self):
		channel = grpc.insecure_channel('localhost:50051')
		stub = buffer_pb2_grpc.Response_ServiceStub(channel)
			#CLIENT.containers.run(name="client", command="sleep infinity", image="ubuntu:latest", detach=True)
		response_string = b"start"
		stub.Info(buffer_pb2.Send_Request(send=response_string))
		term_socket()
				

def term_socket():
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
	Spawn()

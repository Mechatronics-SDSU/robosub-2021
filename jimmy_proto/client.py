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

gate_detector = GateDetector()
cap = cv2.VideoCapture('files/Additional_Test_Video.mp4')
tracking = {}


def run():
	with grpc.insecure_channel('localhost:50051') as channel:
		try:
			stub = buffer_pb2_grpc.Response_ServiceStub(channel)
			i = 0
			p = Process(target=process, args=(cap,stub,i,))
			server.check(p, "start")
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.connect((HOST, PORT))
				print("Inside")
				data = s.recv(1024)
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


def stop():
	server.check(p, "stop")
				
   
if __name__ == '__main__':
	logging.basicConfig()
	run()

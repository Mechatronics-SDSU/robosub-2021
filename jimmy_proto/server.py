from concurrent import futures
import grpc
import buffer_pb2
import buffer_pb2_grpc
import time
import threading
import logging
import pickle
import os
import client
import socket

HOST = '127.0.0.1'
PORT = 65432
SERVER_ADDRESS = "localhost:23333"

class Listener(buffer_pb2_grpc.Response_ServiceServicer):
	def Info(self, request, context):
		retriever = bytes(request.send)
		val = pickle.loads(retriever)
		print(val)
		return buffer_pb2.Request_Response(message = bytes('Bytes Recieved: %s!' % request.send, 'utf-8'))


def check(p, cmd):
	if cmd == "start":
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.bind((HOST,PORT))
			s.listen()
			s.sendall(p.start())
	if cmd == "stop":
		p.kill()
	if cmd == "check":
		print("Is p alive? ", p.is_alive())
		
			
def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	buffer_pb2_grpc.add_Response_ServiceServicer_to_server(Listener(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination()

			
if __name__ == "__main__":
	logging.basicConfig()
	serve()

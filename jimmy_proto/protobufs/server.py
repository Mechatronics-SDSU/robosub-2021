from concurrent import futures
import grpc
import buffer_pb2
import buffer_pb2_grpc
import time
import threading

import os


class Listener(buffer_pb2_grpc.Response_ServiceServicer):
	def __init__(self):
		self.running_targets = []
		
			
def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	buffer_pb2_grpc.add_Response_ServiceServicer_to_server(Listener(), server)
	sever.add_insecure_port("[::]:99999")
	server.start()
	try:
		while True:
			print("server on: threads %i" % (threading.active_count()))
	except KeyboardInterrupt:
		print("KeyboardInterrupt")
		server.stop(0)
			
			
	if __name__ == "__main__":
		serve()

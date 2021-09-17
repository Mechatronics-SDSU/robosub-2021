"""TODO: Add a docstring!
"""
import grpc
import logging
import socket

from src.utils import buffer_pb2, buffer_pb2_grpc

HOST = "0.0.0.0"
PORT = 65432
CLIENT_ID = 1
STARTED = False


class Spawn:
	"""TODO: Add a docstring!
	"""
	def __init__(self):	
		self.run()

	@staticmethod
	def run():
		"""TODO: Add a docstring!
		"""
		channel = grpc.insecure_channel('0.0.0.0:50051')
		stub = buffer_pb2_grpc.Response_ServiceStub(channel)
		response_string = b"start"
		print("Start Command")
		stub.Info(buffer_pb2.Send_Request(send=response_string))
		print("Sending")
		term_socket()
				

def term_socket():
	"""TODO: Add a docstring!
	"""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((HOST, PORT))
		s.listen(5)
		conn, addr = s.accept()
		while STARTED:
			data = conn.recvfrom(1024)[0]
			print(data)
		conn.close()
			
			
def stop():
	"""TODO: Add a docstring!
	"""
	server.check(p, "stop")  # Why is this here? -IAR


if __name__ == '__main__':
	logging.basicConfig()
	Spawn()

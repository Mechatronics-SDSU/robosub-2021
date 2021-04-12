#!/usr/bin/env python3
import socket
from struct import pack
from gen.protobuf import msg_pb2

sock = socket.socket(socket.AF_UNIX)
address = './SOCKETS/test.sock'


msg = msg_pb2.Boring()
msg.cont = "ENCODED  MESSAGE: hello you brute"
encoded = msg.SerializeToString()

try:
	sock.connect(address)
except socket.error as e:
		print(e)
		exit(1)

try:
	x = pack('>I', len(encoded))
	sock.sendall(x)
	sock.sendall(encoded)
except Exception as e:
	print(e)
	exit(1)

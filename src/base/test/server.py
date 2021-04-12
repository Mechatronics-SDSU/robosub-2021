#!/usr/bin/env python3
import socketserver
from struct import unpack
from os import unlink
from gen.protobuf import msg_pb2

def SERVER():
    address = './SOCKETS/test.sock'
    
    class Session(socketserver.BaseRequestHandler):
    	def handle(self):
    		header = self.request.recv(4)
    		message_length, = unpack('>I', header) #unpack always returns a tuple.
    		print(message_length)
    		
    		message = self.request.recv(message_length)
    		pb_message = msg_pb2.Boring()
    		pb_message.ParseFromString(message)
    		
    		print("Message: " + pb_message.cont)
    		
    
    try:
    	unlink(address)
    except OSError as e:
    	pass
    
    server = socketserver.UnixStreamServer(address, Session)
    server.serve_forever()
def CLIENT():
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

if __name__=="__main__":
    import argparse
    import time
    parser = argparse.ArgumentParser(description("Adding Modules into the Docker Container")
    parser.add_argument("cont_type", type=str,
        help="The Container Type, enter either \'server\' or \'client\'")
    args = parser.parse_args()
    
    outfunc = None

    if args.cont_type != None:
        container_type = args.cont_type[0].upper()

        if container_type == "server".upper():
            outfunc = SERVER
        elif container_type == "client".upper():
            def alt_client_func():
                start = time.time()
                while True:
                    if time.time - start > .125 :
                        CLIENT()
                        start = time.time()
                    else:
                        pass
            outfunc = alt_client_func
    else:
        outfunc = lambda x: return None
    print("STARTING ....")
    outfunc()


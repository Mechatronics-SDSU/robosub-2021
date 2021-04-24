#!/usr/bin/env python

from __future__ import division
import cv2
import numpy as np
import socket
import struct

import threading

MAX_DGRAM = 2**16


#class CommandInterpreterService(startstream_pb2_grpc.CommandInterpreterServicer):
#    def GiveCommand(self, request, context):
#        if request.name == "unix video":
#            vid = threading.Thread(target=initiate_unix_video,)
#            vid.start()
#        return startstream_pb2.CommandAck(message="ok: <{}>".format(request.name))

def dump_buffer(s):
    """ Emptying buffer frame """
    while True:
        seg, addr = s.recvfrom(MAX_DGRAM)
        print(seg[0])
        if struct.unpack("B", seg[0:1])[0] == 1:
            print("finish emptying buffer")
            break

#def server():
#    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
#    startstream_pb2_grpc.add_CommandInterpreterServicer_to_server(CommandInterpreter(), server)
#    server.add_insecure_port('unix:///sock/test.sock')
#    server.start()
#    server.wait_for_termination()

def main():
    """ Getting image udp frame &
    concate before decode and output image """
    
    # Set up socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    s.bind("/sock/test.sock")
    dat = b''
    dump_buffer(s)

    while True:
        seg, addr = s.recvfrom(MAX_DGRAM)
        if struct.unpack("B", seg[0:1])[0] > 1:
            dat += seg[1:]
        else:
            dat += seg[1:]
            img = cv2.imdecode(np.fromstring(dat, dtype=np.uint8), 1)
            cv2.imshow('frame', img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            dat = b''

    # cap.release()
    cv2.destroyAllWindows()
    s.close()

if __name__ == "__main__":
    main()

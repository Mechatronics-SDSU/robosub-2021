#!/usr/bin/env python3

import cv2
import numpy as np
import socket
import struct

import threading

MAX_DGRAM = 2**16

def dump_buffer(s):
    """ Emptying buffer frame """
    while True:
        seg, addr = s.recvfrom(MAX_DGRAM)
        print(seg[0])
        if struct.unpack("B", seg[0:1])[0] == 1:
            print("finish emptying buffer")
            break

#class VideoStreamResponseThread(threading.Thread):
#    def __init__(self):
#        threading.Thread.__init__(self)
#        #self.daemon = True
#        self.loopflag = True
#    def kill(self):
#        self.loopflag = False
#        return 0

#def run(self):
def video_stream_response_process():

    """ Getting image udp frame &
    concate before decode and output image """
    
    # Set up socket
    
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind("/sock/video.sock")
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
    s.close()
    cv2.destroyAllWindows()
    print("done")

if __name__ == "__main__":
    main()

"""TODO Add docstring
"""

import grpc
import cv2
import numpy as np
import sys
from threading import Thread
from concurrent import futures
# import numpy as np
# import grpc
# import cv2
# import grpc
import socket
import time
import pickle
# import numpy as np
# import io
# import cv2
import struct

import socket_route_guide_pb2
import socket_route_guide_pb2_grpc
import src.utils.ip_config as ipc
ip = ipc.load_config_from_file('src/utils/ip_config.json')


class SocketConnection:
    """Manages the socket connection
    """
    def __init__(self):
        print('Initialized')
        self.host = ''
        self.port = ip.video_port
        self.started = False
        self.use_udp = False
        if self.use_udp:
            self.t = Thread(target=self.sock_udp, args=())
        else:
            self.t = Thread(target=self.sock_tcp, args=())

    def start(self):
        """Starts the socket server thread
        """
        self.t.start()
        self.started = True
        return self

    def sock_tcp(self):
        """Runs the TCP socket server
        """
        print('Started Thread')
        vs = cv2.VideoCapture(0, cv2.CAP_V4L2)
        vs.set(3, 640)
        vs.set(4, 480)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            conn, address = s.accept()
            print('Received connection from address: ' + str(address))
            while self.started:
                result = conn.recvfrom(1024)[0]
                if result == b'1':
                    img = None
                    _, img = vs.read()
                    if img is not None:
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                        _, response = cv2.imencode('.jpg', img, encode_param)
                        response = pickle.dumps(response, 0)
                        size = len(response)
                        conn.sendall(struct.pack('>L', size) + response)
                        result = 0

    def sock_udp(self):
        """Runs the UDP socket server
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while self.started:
                data, address = s.recvfrom(1024) # b'1'
                print('[SOCK] Socket Received: ' + str(data))
                response = np.asarray(self.vs.read())
                response = response.flatten()
                response = response.tobytes()
                package = [None]*768
                t1 = time.time()
                for i in range(0, 768):  # 768 * 1200 = 640 * 480 * 3
                    # package.append(response[(i*1200):((i+1)*1200)])
                    s.sendto(response[(i*1200):((i+1)*1200)], address)
                # print('[SOCK] Sending response of size ' + str(len(package)*1200))
                t2 = time.time()
                print(str(t2 - t1) + ' seconds')
                s.sendto(b'STOP_CODE', address)
                # print(s.sendto(response, address))
                print('[SOCK] Send complete.')

    def stop(self):
        """Stops the socket server thread
        """
        print('[SOCK] Stopping server...')

        self.t.join()
        self.started = False


class StartSocket(socket_route_guide_pb2_grpc.SocketGRPCServicer):
    """Starts up the socket when the correct MsgRequest protobuf has been received
    """
    def __init__(self):
        print('GRPC init')
        self.socket_server = SocketConnection()

    def SendSocketRequest(self, request, context):
        """Starts up socket server with correct request and returns ack
        :param request:
        :param context:
        :return: MsgReply
        """
        request = request_to_value(str(request))
        print('[GRPC] Received request ' + request + ' from client.')
        if (request == '2') and (not self.socket_server.started):
            self.socket_server = SocketConnection()  # Make a new socket
            self.socket_server.start()
            data = '@' + str(self.socket_server.host) + str(self.socket_server.port)
            print('[GRPC] Sending... [' + data + ']')
            return socket_route_guide_pb2.MsgReply(ack=data)
        elif request == '2':
            print('[GRPC] Server already started, ignoring.')
            return socket_route_guide_pb2.MsgReply(ack='!Warn, start request sent with socket already started')
        # This is where we add other commands for requests
        # For example to stop or restart or modify the socket server
        elif (request == '3') and self.socket_server.started:
            print('[GRPC] STOP code received, shutting down socket server.')
            self.socket_server.stop()
            return socket_route_guide_pb2.MsgReply(ack='@STOP')
        elif request == '3':
            print('[GRPC] Server not yet started and STOP code received, ignoring.')
            return socket_route_guide_pb2.MsgReply(ack='!Warn, stop request sent with socket not started')


def request_to_value(r):
    """Converts responses into strings. For some reason grpc adds quotes
    """
    first = -1
    result = ''
    for i in range(len(r)):
        if r[i] == '\"' and first == -1:
            first = i
        elif r[i] == '\"' and first != -1:
            result = r[first+1:i]
    return result


def main():
    """Driver Code for grpc server
    """
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    socket_route_guide_pb2_grpc.add_SocketGRPCServicer_to_server(StartSocket(), server)
    server.add_insecure_port('[::]:50051')
    print('[@SCKS] Starting socket server...')
    server.start()
    print('[@SCKS] Socket server started.')
    server.wait_for_termination()
    print('[@SCKS] Server\'s closed.')
    """
    sc = SocketConnection()
    sc.start()


if __name__ == '__main__':
    main()
else:
    print('Run me as main!')
    sys.exit()

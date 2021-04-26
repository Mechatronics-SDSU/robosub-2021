# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Python implementation of the GRPC helloworld.CommandInterpreter server."""

from concurrent import futures
import logging
import multiprocessing
import threading
import grpc
import time

import startstream_pb2
import startstream_pb2_grpc

from sender import video_stream_init_process
import os


class CommandInterpreter(startstream_pb2_grpc.CommandInterpreterServicer):

    def __init__(self):
        self.running_targets = []

    def GiveCommand(self, request, context):
        message = None
        if request.message == "start":
            message="start"
            st = multiprocessing.Process(target=video_stream_init_process)
            st.start()
            self.running_targets.append(st)

        elif request.message == "stop":
            message = "stop"
            for service in self.running_targets:
                service.terminate()

            self.running_targets = []

        else:
            message = "Invalid CMD"

        return startstream_pb2.CommandAck(message="ok: "+message)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    startstream_pb2_grpc.add_CommandInterpreterServicer_to_server(CommandInterpreter(), server)
    server.add_insecure_port('unix:///sock/test.sock')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig()
    serve()

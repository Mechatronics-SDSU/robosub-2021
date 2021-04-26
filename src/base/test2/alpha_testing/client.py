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
"""The Python implementation of the GRPC helloworld.CommandInterpreter client."""

from __future__ import print_function
import logging
import time
import grpc
import multiprocessing

import startstream_pb2
import startstream_pb2_grpc

from utilities import AppRunner
from sender import video_stream_init_process



class ContainerControl:
    def __init__(self):
        self.responses = []

    def run(self):
        # NOTE(gRPC Python Team): .close() is possible on a channel and should be
        # used in circumstances in which the with statement does not fit the needs
        # of the code.
        while True:
            try:
                msg = input(">> ")
                if msg == "quit":
                    break
                with grpc.insecure_channel('unix:///sock/test.sock') as channel:
                    stub = startstream_pb2_grpc.CommandInterpreterStub(channel)
                    response = stub.GiveCommand(startstream_pb2.CommandRequest(message=msg))
                    print("Client Recieved Response: " + response.message)
    
                    if response.message == "ok: start":
                        st = multiprocessing.Process(target=video_stream_init_process)
                        st.start()
                        self.responses.append(st)
                    elif response.message == "ok: stop":
                        for resp in self.responses:
                            resp.terminate()
                        print("killed responses")
                    else:
                        print("INVALID COMMAND RECEIVED")
            except Exception as e:
                print(e)
                #print("Warning ... Error Captured")

if __name__ == '__main__':
    logging.basicConfig()
    ctrl = ContainerControl()
    ctrl.run()

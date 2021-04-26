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
"""The Python implementation of the GRPC helloworld.Greeter server."""

from concurrent import futures
import logging
import threading
import grpc
import time

import helloworld_pb2
import helloworld_pb2_grpc

class AppRunner(threading.Thread):
    def __init__(self, target=None, loopflag=None):
        threading.Thread.__init__(self)

        self.target = target
        self.not_killed = True
        #self.daemon = True

        self.loopflag = loopflag
        if loopflag == None:
            self.loopflag = True


    def kill(self):
        self.not_killed = False
        return 0

    def run(self):
        if self.loopflag == False:
            while self.not_killed:
                self.target()
        else:
            self.target(self.not_killed)

        print("done.")
        return 0

# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import startstream_pb2 as startstream__pb2


class CommandInterpreterStub(object):
    """The greeting service definition.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.GiveCommand = channel.unary_unary(
                '/startstream.CommandInterpreter/GiveCommand',
                request_serializer=startstream__pb2.CommandRequest.SerializeToString,
                response_deserializer=startstream__pb2.CommandAck.FromString,
                )


class CommandInterpreterServicer(object):
    """The greeting service definition.
    """

    def GiveCommand(self, request, context):
        """Sends a greeting
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_CommandInterpreterServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'GiveCommand': grpc.unary_unary_rpc_method_handler(
                    servicer.GiveCommand,
                    request_deserializer=startstream__pb2.CommandRequest.FromString,
                    response_serializer=startstream__pb2.CommandAck.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'startstream.CommandInterpreter', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class CommandInterpreter(object):
    """The greeting service definition.
    """

    @staticmethod
    def GiveCommand(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/startstream.CommandInterpreter/GiveCommand',
            startstream__pb2.CommandRequest.SerializeToString,
            startstream__pb2.CommandAck.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
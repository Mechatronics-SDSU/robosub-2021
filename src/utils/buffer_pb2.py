# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: buffer_2.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='buffer_2.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x0c\x62uffer.proto\"\x1c\n\x0cSend_Request\x12\x0c\n\x04send\x18\x01 \x01(\x0c\"#\n\x10Request_Response\x12\x0f\n\x07message\x18\x02 \x01(\x0c\x32>\n\x10Response_Service\x12*\n\x04Info\x12\r.Send_Request\x1a\x11.Request_Response\"\x00\x62\x06proto3'
)




_SEND_REQUEST = _descriptor.Descriptor(
  name='Send_Request',
  full_name='Send_Request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='send', full_name='Send_Request.send', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=16,
  serialized_end=44,
)


_REQUEST_RESPONSE = _descriptor.Descriptor(
  name='Request_Response',
  full_name='Request_Response',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='Request_Response.message', index=0,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=46,
  serialized_end=81,
)

DESCRIPTOR.message_types_by_name['Send_Request'] = _SEND_REQUEST
DESCRIPTOR.message_types_by_name['Request_Response'] = _REQUEST_RESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Send_Request = _reflection.GeneratedProtocolMessageType('Send_Request', (_message.Message,), {
  'DESCRIPTOR' : _SEND_REQUEST,
  '__module__' : 'buffer_pb2'
  # @@protoc_insertion_point(class_scope:Send_Request)
  })
_sym_db.RegisterMessage(Send_Request)

Request_Response = _reflection.GeneratedProtocolMessageType('Request_Response', (_message.Message,), {
  'DESCRIPTOR' : _REQUEST_RESPONSE,
  '__module__' : 'buffer_pb2'
  # @@protoc_insertion_point(class_scope:Request_Response)
  })
_sym_db.RegisterMessage(Request_Response)



_RESPONSE_SERVICE = _descriptor.ServiceDescriptor(
  name='Response_Service',
  full_name='Response_Service',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=83,
  serialized_end=145,
  methods=[
  _descriptor.MethodDescriptor(
    name='Info',
    full_name='Response_Service.Info',
    index=0,
    containing_service=None,
    input_type=_SEND_REQUEST,
    output_type=_REQUEST_RESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_RESPONSE_SERVICE)

DESCRIPTOR.services_by_name['Response_Service'] = _RESPONSE_SERVICE

# @@protoc_insertion_point(module_scope)
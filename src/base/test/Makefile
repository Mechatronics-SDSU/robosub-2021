.PHONY: all
all: gen/msg_pb2.py

gen/msg_pb2.py: ../protobuf/msg.proto
	touch gen/__init__.py # I hate this.
	protoc --python_out=gen -I .. ../protobuf/msg.proto

.PHONY: clean
clean:
	rm -f gen/*

.PHONY: really_clean
really_clean:
	rm -rf gen

## Communication pathway diagram

![pathway diagram](/img/ref_gui_architecture_1.png)

The GUI uses Python's [Multiprocessing](https://docs.python.org/3/library/multiprocessing.html) module to send/receive data into the HOST from the SUB. These processes are kept separate from one another for both performance and architectural reasons. The GUI's actual window frame seen by the Operator on HOST is also in its own process. All of these modules communicate over multiprocessing pipes and pass messages through a routing process. Pipes have 2 ends which are capable of holding data. This system was designed such that one end of the pipe is polled for new data, and one end of the pipe is used to send data. This is used for organizational reasons, to have one end of the pipe always being the input (source of information) and the other end of the pipe always being the output (destination of information). 

The table below refers to these pipes. Identifiers are not used in the code, but are used here to represent which pipes are the same pipe objects. Each Identifier has an input and an output associated with it. Communication is the main function of pipes to pass messages between processes, but other pipes exist. Their function is listed in the table.

Pipe Identifier | Pipe Name | Process on this end of pipe | Pipe Type | Function
---------------- | ---------------- | ---------------- | ---------------- | ----------------
0 | pipe_to_gui_from_router | Router | OUT | Communication
0 | gui_pipe_in_from_router | GUI | IN | Communication
1 | pipe_to_router_from_gui | GUI | OUT | Communication
1 | pipe_in_from_gui | Router | IN | Communication
2 | pipe_to_video_from_router | Router | OUT | Communication
2 | vid_pipe_in_from_router | Video Socket | IN | Communication
3 | pipe_to_router_from_video | Video Socket | OUT | Communication
3 | pipe_in_from_video | Router | IN | Communication
4 | pipe_to_gui_from_video | Video Socket | OUT | Sends frame data from socket
4 | pipe_in_from_video_stream | GUI | IN | Receives frame data to display in GUI
5 | pipe_to_logging_from_router | Router | OUT | Communication
5 | log_pipe_in_from_router | Logging Socket | IN | Communication
6 | pipe_to_router_from_logger | Logging Socket | OUT | Communication
6 | pipe_in_from_logger | Router | IN | Communication
7 | pipe_to_telemetry_from_router | Router | OUT | Communication
7 | tel_pipe_in_from_router | Telemetry Socket | IN | Communication
8 | pipe_to_router_from_telemetry | Telemetry Socket | OUT | Communication
8 | pipe_in_from_telemetry | Router | IN | Communication
9 | pipe_to_pilot_from_router | Router | OUT | Communication
9 | plt_pipe_in_from_router | Pilot Socket | IN | Communication
10 | pipe_to_router_from_pilot | Pilot Socket | OUT | Communication
10 | pipe_in_from_pilot | Router | IN | Communication
11 | pipe_to_pilot_from_gui | GUI | OUT | Sends controller data to socket
11 | pilot_pipe_in_from_gui | Pilot Socket | IN | Receives controller input to send to SUB

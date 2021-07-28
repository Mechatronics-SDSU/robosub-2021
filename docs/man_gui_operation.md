## GUI Operator Manual

This is the operator manual for the GUI. If the GUI and its dependencies are not yet installed on your computer, see man_host_setup.md for build instructions.

#### Layout

#### Startup

#### Setting IP configuration
To set the IP config on the GUI, you can click the `Remote IP` button at the top of the GUI. You can set the IP on the remote address here. The default address is localhost for testing and the current destination is shown on the display. To change the ports on the sockets and grpc from the defaults, see the `ip_config.py` file about setting the IP. You currently need to enter interactive mode in python and set the relevant ports and call the save function. This may be changed later.

#### Command Configuration
Command Configuration packets control Pico's initial setup state. Before a connection is established, the config must be set so Pico knows what subsystems to turn on. 

Subsystem | Option 1 | Option 1 Function | Option 2 | Option 2 Function | Option 3 | Option 3 Function
------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- 
Video | Enable | Enables Pico's camera socket | Disable | Disable Pico's camera socket | N/A | N/A
Logging | Debug | Enables Pico's logging at debug level (most information) | Info | Enables Pico's logging at info level (important information) | Disable | Disables Pico's logging socket
Telemetry | Enable | Enable Pico's Telemetry socket to send sensor data back | Disable | Disable Pico's telemetry socket, sensor data not sent back | N/A | N/A
Pilot | Enable | Enable Pico's Pilot socket, allows for manual control | Disable | Disable Pico's pilot socket, enables autonomous control | N/A | N/A
Mission | All | Does all missions in order when pilot is off | Mission | Does specific mission when pilot is off | None | Does no missions

#### Controller inputs

#### Misc


## GUI Operator Manual

This is the operator manual for the GUI. If the GUI and its dependencies are not yet installed on your computer, see man_host_setup.md for build instructions.

### Layout

#### System Logs
System logs are logs from both Pico and the GUI. The GUI's messages will be preceded with a `@` sign to reference which GUI subsystem is responsible for generating the message, as described in the below table. (((add later))) Messages from Pico will be preceded with a `#` sign to reference which of Pico's subsystems is responsible for generating the message.
Pico's logging system uses python's own logger and implements related logging levels. See the misc section for more information. (((add later)))
The HOST GUI uses its own logging system and will only log warnings, errors, and critical problems to the logger.

#### Video Stream
The GUI video steam is a live video feed from Pico that only receives frames when a socket connection is established. If a frame is frozen on this window, it is likely because of a connection loss, but hardware failure for Pico's camera system or other systems is possible. The system attempts to re-establish a connection if it is due to a connection loss. Persistent frame freezing could be from other issues.

#### Comms Status
The HOST computer establishes various connections with Pico over UNIX sockets and GRPC. This is where that information is displayed.

#### HOST Status
The HOST computer and the GUI will display information here, such as if the config is set, if the controller is ready, and if controls are inverted.

#### Pico Status
If the HOST is connected to Pico's Commande Configuration GRPC and telemetry is enabled, Pico's state is shown here.

#### Inputs/Thruster levels
Inputs are the raw controller inputs from the Pilot on the controller plugged in to the HOST machine. They are visually represented in the inputs section.

Thruster levels are the translated controller inputs from the controller and are the actual values being sent to the thrusters via the maestro controller. Valid values are from -100 to 100. Negative bars going down are -100 to 0, positive bars going up are 0 to 100.

#### Graphing
The GUI graphing utility displays the data shown as a function of time, measured in seconds. The graphs can be switched by pressing the left and right buttons to cycle through whatever graph is needed at a perticular time. If no measurment is received from sensors being disabled, the graph will set the value to 0.

#### Sensor Data
All sensor data from Pico's telemetry socket is displayed here.

### Startup

### Setting IP configuration
To set the IP config on the GUI, you can click the `Remote IP` button at the top of the GUI. You can set the IP on the remote address here. The default address is localhost for testing and the current destination is shown on the display. To change the ports on the sockets and grpc from the defaults, see the `ip_config.py` file about setting the IP. You currently need to enter interactive mode in python and set the relevant ports and call the save function. This may be changed later.

### Command Configuration
Command Configuration packets control Pico's initial setup state. Before a connection is established, the config must be set so Pico knows what subsystems to turn on. 

Subsystem | Option 1 | Option 1 Function | Option 2 | Option 2 Function | Option 3 | Option 3 Function
------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- 
Video | Enable | Enables Pico's camera socket | Disable | Disable Pico's camera socket | N/A | N/A
Logging | Debug | Enables Pico's logging at debug level (most information) | Info | Enables Pico's logging at info level (important information) | Disable | Disables Pico's logging socket
Telemetry | Enable | Enable Pico's Telemetry socket to send sensor data back | Disable | Disable Pico's telemetry socket, sensor data not sent back | N/A | N/A
Pilot | Enable | Enable Pico's Pilot socket, allows for manual control | Disable | Disable Pico's pilot socket, enables autonomous control | N/A | N/A
Mission | All | Does all missions in order when pilot is off | Mission | Does specific mission when pilot is off | None | Does no missions

### Controller inputs

### Misc


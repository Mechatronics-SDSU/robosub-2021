"""Defines the class to be serialized and sent over grpc.

Code revision is used to maintain a consistency between client and server.
When the following codes are modified, increment the code revision in this class.
The server's code should verify its code revision with the client and return some
error over grpc if its code is not the same. This should futureproof the sub and
prevent mistakes.

Subsystem socket codes: A python list of integers of all subsystems. 
Index of the list is the subsystem and the value at index is the mode it will be placed in.
(Might make this an enum?)
Index:
0: LOGS (Intelligence high-level logging)
1: VIDEO (Inference video stream)
2: TELEMETRY (Control sensor data)

LOGS index[0]:
0: Disable Logging Socket.
1: Enable Logging Socket, logging everything.
2: Enable Logging Socket, logging only important information.

VIDEO index[1]:
0: Disable Video Socket.
1: Enable Video Socket.

TELEMETRY index[2]:
0: Disable Telemetry Socket.
1: Enable Telemetry Socket, sending only important information.

On class initialization these are initialized to 0. 0 will be an invalid default value and
will return errors if not modified.

Manual robot control: A boolean for if the sub is in pilot mode or autonomous mode.
On class initialization this is initialized to True. This will be a valid default value
for operation and will only be modified via changing driver code or through GUI.

Mission: A string for what mission the sub will be running while in autonomous mode.
Missions will be listed here:
'no': The sub has no mission and will remain idle.
'all': The sub will do all missions in subsequent order.
'gate': Gate mission.
'buoy': Bump Buoy mission.
'rise': Rising in square mission.

On class initialization this is initialized to 'no' for no mission. This will be a valid default value
for operation and will only be modified via changing driver code or through GUI.
"""


class CommandConfiguration:
    """Contains class data as described in docstring. Validates arguments and assigns default
    values if not specified.
    """

    def __init__(self, socket_codes, pilot_control, mission):
        # See docstring for documentation on these codes
        self.code_revision = 1  # How many times have the codes been modified/added to?
        self._DEFAULT_LOGGING_CODE = 0  # Might want to change this to log important only by default
        self._DEFAULT_LOGGING_CODE_MAX = 2
        self._DEFAULT_VIDEO_CODE = 0
        self._DEFAULT_VIDEO_CODE_MAX = 1
        self._DEFAULT_TELEMETRY_CODE = 1
        self._DEFAULT_TELEMETRY_CODE_MAX = 1
        self._DEFAULT_SOCK_CODES = (self._DEFAULT_LOGGING_CODE,
                                    self._DEFAULT_VIDEO_CODE,
                                    self._DEFAULT_TELEMETRY_CODE)
        self._DEFAULT_SOCK_CODES_MAX = (self._DEFAULT_LOGGING_CODE_MAX,
                                        self._DEFAULT_VIDEO_CODE_MAX,
                                        self._DEFAULT_TELEMETRY_CODE_MAX)
        self._DEFAULT_PILOT_CONTROL = False
        self._VALID_MISSIONS = ('no', 'all', 'gate', 'buoy', 'rise')
        self._DEFAULT_MISSION = 'no'

        self.socket_codes = []
        # Verify all socket codes passed are valid. Set to default and warn otherwise.
        for i in range(len(socket_codes)):
            if self._DEFAULT_SOCK_CODES_MAX[i] < socket_codes[i]:
                print('[CMDC] !Warn, invalid socket_code ' + str(socket_codes[i]) +
                      ' passed, defaulting to ' + str(self._DEFAULT_SOCK_CODES[i]))
                self.socket_codes.append(self._DEFAULT_SOCK_CODES[i])
            else:
                self.socket_codes.append(socket_codes[i])

        # Verify pilot control is a boolean. Set to default and warn otherwise.
        self.pilot_control = None
        if pilot_control is True:
            self.pilot_control = True
        elif pilot_control is False:
            self.pilot_control = False
        else:
            print('[CMDC] !Warn, invalid pilot_control arg ' + str(pilot_control) +
                  ' passed, defaulting to ' + str(self._DEFAULT_PILOT_CONTROL))
            self.pilot_control = self._DEFAULT_PILOT_CONTROL

        # Verify mission string is a valid mission. Set to default and warn otherwise.
        self.mission = ''
        for i in range(len(self._VALID_MISSIONS)):
            if mission == self._VALID_MISSIONS[i]:
                self.mission = mission
        if self.mission == '':
            print('[CMDC] !Warn, invalid mission ' + str(mission) +
                  ' passed, defaulting to ' + str(self._DEFAULT_MISSION))
            self.mission = self._DEFAULT_MISSION

    def gen_packet(self):
        """Builds a CommandConfigurationPacket with the information passed to this
        class's constructor.
        :return: CommandConfigurationPacket object
        """
        cmd_conf_packet = CommandConfigurationPacket(self)
        return cmd_conf_packet

    def __str__(self):
        """Overrides the print method to show data stored.
        """
        return 'Command Configuration object ' + \
               ' Socket codes:' + str(self.socket_codes) + \
               ' Pilot_Testing control: ' + str(self.pilot_control) + \
               ' Mission selected: ' + str(self.mission)


class CommandConfigurationPacket:
    """The class that is serialized and sent over grpc.
    Much of the data saved as class members in the CommandConfiguration class
    are checkers to validate data being sent. This data isn't necessary to send
    over grpc because both client and server will have that information.
    This class does no checking and relies on the checking from
    CommandConfiguration to generate and send valid codes.
    """

    def __init__(self, config):
        self.revision = config.code_revision
        self.logging_code = config.socket_codes[0]
        self.video_code = config.socket_codes[1]
        self.telemetry_code = config.socket_codes[2]
        self.pilot_control = config.pilot_control
        self.mission = config.mission


if __name__ == '__main__':
    print('Don\'t run me as main!')

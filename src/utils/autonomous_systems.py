"""Defines relevant classes and methods for Pico's autonomous systems.

When running autonomously, it is necessary for Pico to have many relevant functions on board instead of human input.
Classes defined here will be instantiated and used for various Control and Intelligent systems, but ONLY when Pico
is running autonomously. These are NOT TO BE USED when Pico is being manually controlled.
"""

import copy


# List of all directive names by string and by index.
move_directives_by_str = {
    'STATIONARY': 0,  # Do not alter bearing
    'MOVE': 1,  # Maintain bearing, change position relative to >= 1 axis
    'TURN': 2,  # Maintain position, change bearing relative to >= P/R/Y bearings
    'MULTIDIRECTIVE': 3  # Change bearing and position
}
move_directives_by_index = {
    0: 'STATIONARY',  # Do not alter bearing
    1: 'MOVE',  # Maintain bearing, change position relative to >= 1 axis
    2: 'TURN',  # Maintain position, change bearing relative to >= P/R/Y bearings
    3: 'MULTIDIRECTIVE',  # Change bearing and position
}

# List of all directions by string and index
move_directions_by_index = {
    0: 'FORWARD',
    1: 'BACKWARDS',
    2: 'DOWN',
    3: 'UP',
    4: 'LEFT',
    5: 'RIGHT',
    6: 'INPLACE_LEFT',
    7: 'INPLACE_RIGHT',
    8: 'INVERTED_LEFT',
    9: 'INVERTED_RIGHT'
}
move_directions_by_str = {
    'FORWARD': 0,
    'BACKWARDS': 1,
    'DOWN': 2,
    'UP': 3,
    'LEFT': 4,
    'RIGHT': 5,
    'INPLACE_LEFT': 6,
    'INPLACE_RIGHT': 7,
    'INVERTED_LEFT': 8,
    'INVERTED_RIGHT': 9
}
thruster_key = {
    0: 2,
    1: 2,
    2: 0,
    3: 0,
    4: -1,
    5: -1,
    6: 0,
    7: 0,
    8: 0,
    9: 0
}
modification_table = {
    0: 1,
    1: -1,
    2: 1,
    3: -1,
    4: -1,
    5: -1,
    6: -1,
    7: -1,
    8: -1,
    9: -1
}
# Thruster configuration names and indexes
complement_thrusters = {
    0: 1,  # PFZT / SFZT
    1: 0,
    3: 4,  # PAZT / SAZT
    4: 3,
    2: 5,  # PYT / SYT
    5: 2
}
thrusters_by_str = {
    'PFZT': 0,
    'SFZT': 1,
    'SYT': 2,
    'SAZT': 3,
    'PAZT': 4,
    'PYT': 5
}
thrusters_by_index = {
    0: 'PFZT',
    1: 'SFZT',
    2: 'SYT',
    3: 'SAZT',
    4: 'PAZT',
    5: 'PYT'
}


class MoveDirectiveTranslator:
    """The move directive translator will convert thruster instructions to high-level human-readable commands.
    """
    def __init__(self):
        self._state = [0, 0, 0, 0, 0, 0]

    def get_state(self):
        return self._state

    def set_state_from_raw(self, new_state: list) -> None:
        if isinstance(new_state, list):
            self._state = new_state

    def set_state_from_hi(self, new_state: list) -> int:
        """Modifies the state from a high-level directive to a low-level thruster input.
        """
        if not isinstance(new_state, list):
            return 0
        if new_state[0] == 'STATIONARY':  # No movement
            self._state = [0, 0, 0, 0, 0, 0]
            return 1
        elif new_state[0] == 'MOVE':  # Directional (no turn) movement
            if (new_state[1] == 'FORWARD') or (new_state[1] == 'BACKWARD'):
                for i in range(6):
                    if i == thruster_key[move_directions_by_str[new_state[1]]]:
                        self._state[i] = new_state[2] * modification_table[move_directions_by_str[new_state[1]]]
                    elif i == complement_thrusters[thruster_key[move_directions_by_str[new_state[1]]]]:
                        self._state[i] = new_state[2] * modification_table[move_directions_by_str[new_state[1]]]
                    else:
                        self._state[i] = 0


class AutoThrusters:
    """AutoThruster class translates high-level directives into thruster controls along with relevant methods
    for serialization to and from bytes.
    """
    def __init__(self):
        self.thruster_inputs = None

    def translate_to_bytes(self) -> bytes:
        """Translates thruster inputs to unsigned bytes.
        Adds 100 s/t:
        -100 (lowest thruster value) = 0
        100 (highest thruster value) = 200
        This allows us to send negative values as long as we subtract 100 on the other end.
        """
        retval = copy.deepcopy(self.thruster_inputs)
        for i in range(len(retval)):
            retval[i] += 100
        return bytes(retval)

    def translate_from_bytes(self, byte_list: bytes) -> None:
        """Translates bytes objects received on network back into thruster inputs.
        """
        new_list = list(byte_list)
        for i in range(len(new_list)):
            new_list[i] += -100
        self.thruster_inputs = copy.deepcopy(new_list)


def main():
    pass


if __name__ == '__main__':
    main()

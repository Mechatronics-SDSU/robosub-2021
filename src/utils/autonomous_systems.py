"""Defines relevant classes and methods for Pico's autonomous systems.

When running autonomously, it is necessary for Pico to have many relevant functions on board instead of human input.
Classes defined here will be instantiated and used for various Control and Intelligent systems, but ONLY when Pico
is running autonomously. These are NOT TO BE USED when Pico is being manually controlled.
"""

import copy


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
        """Translates bytes objects received on network back into thrusster inputs.
        """
        new_list = list(byte_list)
        for i in range(len(new_list)):
            new_list[i] += -100
        self.thruster_inputs = copy.deepcopy(new_list)

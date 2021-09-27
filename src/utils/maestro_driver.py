"""Blake's Maestro Driver code, with some formatting, cleanup, arguments.
https://www.pololu.com/docs/0J40 link to maestro documentation
"""

import serial
import struct
import time


class MaestroDriver:
    """Controls the Maestro.
    """
    def __init__(self, com_port, baud_rate=115200,
                 lower_pulse_bound=1100,
                 upper_pulse_bound=1900,
                 most_recent_thrusts=None):
        if most_recent_thrusts is None:
            most_recent_thrusts = [0, 0, 0, 0, 0, 0]
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.lower_pulse_bound = lower_pulse_bound
        self.upper_pulse_bound = upper_pulse_bound

        self.usb = serial.Serial(com_port)
        self.most_recent_thrusts = most_recent_thrusts

    def set_thrusts(self, thrusts=None):
        """Sets thrusters.
        :param thrusts:
        :return:
        """
        if thrusts is None:
            thrusts = [0, 0, 0, 0, 0, 0]
        for i in range(6):
            if thrusts[i] < -100 or thrusts[i] > 100 or len(thrusts) != 6:
                thrusts = MaestroDriver.most_recent_thrusts
        old_range = (100 + 100)
        new_range = (1900 - 1100)
        pulse_width = []
        # populating pulse width array
        for t in thrusts:
            if t < 0:  # Negative value check for clockwise motor spin
                t = t + 100
                pulse_width.append(abs((((t + 100) * new_range) / old_range) + 700))
            else:
                pulse_width.append((((t + 100) * new_range) / old_range) + 1100)

            pulse_width[-1] = round(pulse_width[-1] * 4)/4
        self.most_recent_thrusts = pulse_width

        # packing pulse width command
        for i in range(6):
            a = int(pulse_width[i] * 4)
            lower_bits = a & 0x7f
            upper_bits = (a >> 7) & 0x7f
            pulse_width_packed = struct.pack('>hh', lower_bits, upper_bits)
            message = bytearray([0x84, i, pulse_width_packed[1], pulse_width_packed[3]])
            self.usb.write(message)


if __name__ == "__main__":
    maestro_driver = MaestroDriver("/dev/ttyACM0")
    # arming sequence
    maestro_driver.set_thrusts([50, 50, 50, 50, 50, 50])
    time.sleep(0.1)
    maestro_driver.set_thrusts([0, 0, 0, 0, 0, 0])
    time.sleep(0.1)

    # following code goes from 0 to full power for each thruster
    # (0-100/1100-1900us) then gradually steps down
    ''' 
    for j in range(6):
        thrusts = [0, 0, 0, 0, 0, 0]
        i = 0
        while i < 100:
            thrusts[j] = i
            maestro_driver.set_thrusts(thrusts)
            i += 1
            time.sleep(0.1)
        while i > 0:
            thrusts[j] = i
            maestro_driver.set_thrusts(thrusts)
            i -= 1
            time.sleep(0.1)
    '''
    print('Driving at +100')
    maestro_driver.set_thrusts([0, 0, 100, 0, 0, 100])
    time.sleep(1)
    print('Driving at +75')
    maestro_driver.set_thrusts([0, 0, 75, 0, 0, 75])
    time.sleep(1)
    print('Driving at +50')
    maestro_driver.set_thrusts([0, 0, 50, 0, 0, 50])
    time.sleep(1)
    print('Driving at +25')
    maestro_driver.set_thrusts([0, 0, 25, 0, 0, 25])
    time.sleep(1)
    print('Driving at 0')
    maestro_driver.set_thrusts([0, 0, 0, 0, 0, 0])
    time.sleep(1)
    print('Driving at -25')
    maestro_driver.set_thrusts([0, 0, -25, 0, 0, -25])
    time.sleep(1)
    print('Driving at -50')
    maestro_driver.set_thrusts([0, 0, -50, 0, 0, -50])
    time.sleep(1)
    print('Driving at -75')
    maestro_driver.set_thrusts([0, 0, -75, 0, 0, -75])
    time.sleep(1)
    print('Driving at -100')
    maestro_driver.set_thrusts([0, 0, -100, 0, 0, -100])
    time.sleep(1)
    print('Driving at 0')
    maestro_driver.set_thrusts([0, 0, 0, 0, 0, 0])
    time.sleep(1)
    print('Driving DOWN at 100')
    maestro_driver.set_thrusts([100, 100, 0, 100, 100, 0])
    time.sleep(1)
    print('Driving UP at 100')
    maestro_driver.set_thrusts([-100, -100, 0, -100, -100, 0])
    time.sleep(1)
    maestro_driver.set_thrusts([0, 0, 0, 0, 0, 0])

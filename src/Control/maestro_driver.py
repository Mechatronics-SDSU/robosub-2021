#!/usr/bin/env python3
import struct
import serial
import time

class Maestro_Driver:
    def __init__(self, com_port, baud_rate=115200,
                 lower_pulse_bound=1100,
                 upper_pulse_bound=1900):
        '''
        Establish serial com with the MaestroMicro

        :param com_port - Name of the communication port the Maestro is connected to
        :param baud_rate - Typically 115200 baud for the maestro.
        :param lower_pulse_bound - The minimum pulse width in microseconds
        :param upper_pulse_bound - The maximum pulse width in microseconds
        '''
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.lower_pulse_bound = lower_pulse_bound
        self.upper_pulse_bound = upper_pulse_bound

        self.usb = serial.Serial(com_port)

    def set_thrusts(self, thrusts=None):
        '''
        Convert thrust commands to pulsewidth, and send to each of the MicroMaestros 6 channels.

        :param thrusts - List of 6 values, each in range [-100.0, 100.0] to be mapped linearly to
                         pulse widths to send to the maestro. Think of each values as the "percentage of motor
                         speed with respect to max motor speed"
        '''
        if thrusts is None:
            thrusts = [0, 0, 0, 0, 0, 0]

        old_range = (100 + 100)
        new_range = (1900 - 1100)
        pulse_width = []

        #populating pulse width array
        for t in thrusts:
            pulse_width.append((((t + 100) * new_range) / old_range) + 1100)
            pulse_width[-1] = round(pulse_width[-1] * 4)/4

        #packing pulse width command
        for i in range(6):
            a = int(pulse_width[i] * 4)
            lower_bits = a & 0x7f
            upper_bits = (a >> 7) & 0x7f
            pulse_width_packed = struct.pack('>hh', lower_bits, upper_bits)
            message = bytearray([0x84, i, pulse_width_packed[1], pulse_width_packed[3]])
            self.usb.write(message)

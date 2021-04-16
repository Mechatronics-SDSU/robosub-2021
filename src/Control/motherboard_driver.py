#!/usr/bin/env python3

import serial
import struct

class Motherboard_Driver:
    
    def __init__(self, com_port, baud_rate=115200):
        
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.ser = serial.Serial(self.com_port, self.baud_rate)
        
        self.HEADER_BYTE =    0xA4
        self.DEPTH_REQ_BYTE = 0x02
        self.IMU_REQ_BYTE =   0x03
        self.ALL_REQ_BYTE =   0x04
        self.END_BYTE =       0xA0
        
        
    def get_all_sensor_data(self):
        '''
        '''
        
        req_packet = bytearray([self.HEADER_BYTE, self.ALL_REQ_BYTE, self.END_BYTE])
        self.ser.write(req_packet)
        return(self._unpack(self.ALL_REQ_BYTE))
    
    def _unpack(self, requested_packet_type):
        '''
        Unpack the data received after a request is sent to the motherboard.
        Only receive the packet type requested
        '''
        
        if self.ser.in_waiting > 0:
            header_byte = ord(self.ser.read())
            
            if(hex(header_byte) == hex(self.HEADER_BYTE)):
                msg_type = ord(self.ser.read())
                
                if((hex(msg_type) == hex(self.ALL_REQ_BYTE)) and (requested_packet_type == self.ALL_REQ_BYTE)):
                    
                    data_temp = self.ser.read(16)
                    data = struct.unpack('<ffff', data_temp)
                    
                else:
                    return(None)
                
                end_byte = ord(self.ser.read())
                if(hex(end_byte) == "0xa0"):
                    return(data)
                else:
                    return(None)
            else:
                return(None)

import serial
import struct
import time

class Motherboard_Driver:

    def __init__(self, com_port , baud_rate=115200):

        self.com_port = com_port
        self.baud_rate = baud_rate
        self.ser = serial.Serial(self.com_port, self.baud_rate, timeout=.1)
        print(self.ser)
        self.HEADER_BYTE = 164  # A4
        self.END_BYTE = 160  # A0
        self.GET_IMU_DATA = 0x02
        self.GET_DEPTH = 3
        self.GET_BATT_STATUS = 0x04
        self.GET_KILL_STATE = 0x05   #returns 0x01 or 0x00
        self.GET_AUTO_STATE = 0x06
        self.SET_KILL_STATE = 0x07 #Should also send back kill state.

    def get_IMU_data(self):

        req_packet = bytearray([self.HEADER_BYTE, self.GET_IMU_DATA, self.END_BYTE])
        self.ser.write(req_packet)
        return self._unpack(self.GET_IMU_DATA)

    # Add a timeout
    def get_depth(self):

        req_packet = bytearray([self.HEADER_BYTE, self.GET_DEPTH, self.END_BYTE])
        print("Num bytes written: " + str(self.ser.write(req_packet)))

        time.sleep(0.5)  # debug only
        return self._unpack(self.GET_DEPTH)

    def GET_BATT_STATUS(self):

        req_packet = bytearray([self.HEADER_BYTE, self.GET_BATT_STATUS, self.END_BYTE])
        print(req_packet)
        self.ser.write(req_packet)
        return self._unpack(self.GET_BATT_STATUS)

    def _unpack(self, requested_packet_type):

        """
        Unpack the data received after a request is sent to the motherboard.
        Only receive the packet type requested
        """

        if self.ser.in_waiting > 0:
            header_byte = ord(self.ser.read())
            print("Serial buffer is recieving")
            print(hex(header_byte))
            if hex(header_byte) == hex(self.HEADER_BYTE) and self.ser.in_waiting:
                msg_type = ord(self.ser.read())
                print(hex(msg_type))
                if (hex(msg_type) == hex(self.GET_DEPTH)) and (requested_packet_type == self.GET_DEPTH):
                    print("Unpacking data")
                    data_temp = self.ser.read(4)
                    data = struct.unpack('<f', data_temp)
                else:
                    return "Message type and request type dont match"

                # verify end byte
                end_byte = ord(self.ser.read())
                if hex(end_byte) == hex(self.END_BYTE):
                    return data
                else:
                    return "Invalid end byte"
            elif hex(header_byte) == hex(self.HEADER_BYTE):
                return "Start byte received, but no further information sent."
            else:
                return "Invalid start byte"
        else:
            return "No serial in waiting"

if __name__ == "__main__":

    motherboard_driver = Motherboard_Driver('COM3')
    depth = motherboard_driver.get_depth()
    print(depth)

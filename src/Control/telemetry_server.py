"""Driver code for sending telemetry to HOST from SUB.

Currently implementes a random set of sensor data, initialized to floats. See telemetry.py for more information.
The commented out code in run_server describes how loading data would look, given real data.
"""

import numpy as np
import socket

from src.utils.telemetry import Telemetry
import src.utils.ip_config as ipc
ip = ipc.load_config_from_file('src/utils/ip_config.json')


def run_server():
    """Server's driver code
    """
    # Sensors
    '''Here we implement all relevant control code to read in sensor data and load it into Telemetry class.
    Here it is randomized as an example to send back to client but it can be real or simulated.
    See telemetry.py for how to load data into the list.
    '''
    # your_sensor_data_here = [accelerometer_sensor_here, magnetometer_sensor_here,...etc]
    # data = Telemetry()
    # data.load_data_from_array(your_sensor_data_here)

    # Socket connection
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', ip.telemetry_port))
        s.listen()
        conn, address = s.accept()
        print('Listening...')
        while True:
            result = conn.recvfrom(1024)[0]
            if result == b'1':  # Data request
                data = Telemetry(rand_data=True)  # Testing only, replace with actual sensors
                conn.sendall(data.to_bytes())


def main(start=False):
    """Control code to start and stop the server
    """
    while True:
        if not start:
            pass
        else:
            run_server()


if __name__ == '__main__':
    main(start=True)

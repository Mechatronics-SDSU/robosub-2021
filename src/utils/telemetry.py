"""Contains telemetry class data and related methods.
Telemetry is instantiated and assigns all sensors in dictionary to 0. This case assumes the implementer will have
a list of all sensors that they can load by calling the load_data_from_array method after making a new Telemetry
object.

A rand_data argument has been added for testing purposes to verify methods work and data is being sent.
Default argument is False to ensure this isn't used except for testing.

Usage:
1. a. Either make a python list that has all elements in order as defined in Telemetry's sensors dict
and then call load_data_from_array(),
or b. Call Telemetry with the rand_data argument to be True. This will fill the dict with randomized data for testing.
2. Export the data in a numpy array with to_bytes.
3. Import the data with load_data_from_bytes.
"""

import random

import numpy as np


class Telemetry:
    """Handles telemetry data and prepares it for sending back to HOST.
    """
    def __init__(self, rand_data=False):
        self._randomize = rand_data
        self.loaded = False  # Check if data is loaded
        self.sensors = {
            'accelerometer_x': float,
            'accelerometer_y': float,
            'accelerometer_z': float,
            'magnetometer_x': float,
            'magnetometer_y': float,
            'magnetometer_z': float,
            'pressure_transducer': float,
            'gyroscope_x': float,
            'gyroscope_y': float,
            'gyroscope_z': float,
            'voltmeter': float,
            'battery_current': float,
            'roll': float,
            'pitch': float,
            'yaw': float,
            'auto_button': float,
            'kill_button': float
        }
        if not self._randomize:
            for i in self.sensors:
                self.sensors[i] = 0.0
        else:
            for i in self.sensors:
                self.sensors[i] = random.random()
            self.loaded = True

    def load_data_from_array(self, data):
        """
        :param data: List of data to be loaded into this class
        :return: If it worked
        """
        if isinstance(data, list) and not self.loaded:  # Received list of vals, convert to member dict
            counter = 0
            for i in self.sensors:
                self.sensors[i] = data[counter]
                counter += 1
            return True
        else:  # Failed to load list arg or data already loaded
            return False

    def load_data_from_bytes(self, data):
        """Load a bytes object into a numpy array
        :param data: Converted numpy array using tobytes
        :return If it worked
        """
        if isinstance(data, bytes) and not self.loaded:  # Received numpy array, convert numpy array to class
            # Load numpy array into class data
            loaded_data = np.frombuffer(data, dtype=float)
            counter = 0
            for i in self.sensors:
                try:
                    self.sensors[i] = loaded_data[counter]
                    counter += 1
                except IndexError:
                    return False
            return True
        else:  # Failed to load numpy array from bytes or data already loaded
            return False

    def to_bytes(self):
        """Converts class data into a numpy array.
        :return: Bytes object of numpy data.
        """
        result = np.zeros(shape=(1, 17))
        counter = 0
        for i in self.sensors:
            result.put(counter, self.sensors[i])
            counter += 1
        return result.tobytes()


if __name__ == '__main__':
    print('Don\'t run me as main!')

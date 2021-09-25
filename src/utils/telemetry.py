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
import datetime


class Telemetry:
    """Handles telemetry data and prepares it for sending back to HOST.
    """
    def __init__(self, rand_data=False, timestamp=False) -> None:
        self._randomize = rand_data
        self._timestamp = timestamp
        self.loaded = False  # Check if data is loaded
        self.sensors = {
            'no_data': float,
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
            'battery_1_voltage': float,
            'battery_2_voltage': float,
            'roll': float,
            'pitch': float,
            'yaw': float,
            'auto_button': float,
            'kill_button': float
        }
        self.time_series = {
            'no_data': 0.0,
            'accelerometer_x': 0.0,
            'accelerometer_y': 0.0,
            'accelerometer_z': 0.0,
            'magnetometer_x': 0.0,
            'magnetometer_y': 0.0,
            'magnetometer_z': 0.0,
            'pressure_transducer': 0.0,
            'gyroscope_x': 0.0,
            'gyroscope_y': 0.0,
            'gyroscope_z': 0.0,
            'voltmeter': 0.0,
            'battery_current': 0.0,
            'battery_1_voltage': 0.0,
            'battery_2_voltage': 0.0,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'auto_button': 0.0,
            'kill_button': 0.0
        }
        self.index_reference = {
            0: 'no_data',
            1: 'accelerometer_x',
            2: 'accelerometer_y',
            3: 'accelerometer_z',
            4: 'magnetometer_x',
            5: 'magnetometer_y',
            6: 'magnetometer_z',
            7: 'pressure_transducer',
            8: 'gyroscope_x',
            9: 'gyroscope_y',
            10: 'gyroscope_z',
            11: 'voltmeter',
            12: 'battery_current',
            13: 'battery_1_voltage',
            14: 'battery_2_voltage',
            15: 'roll',
            16: 'pitch',
            17: 'yaw',
            18: 'auto_button',
            19: 'kill_button'
        }
        if not self._randomize:
            for i in self.sensors:
                self.sensors[i] = 0.0
                if self._timestamp:
                    self.time_series[i] = datetime.datetime.utcnow().timestamp()
        else:
            for i in self.sensors:
                self.sensors[i] = random.random()
                if self._timestamp:
                    self.time_series[i] = datetime.datetime.utcnow().timestamp()

    def load_data_from_array(self, data: list) -> bool:
        """
        :param data: List of data to be loaded into this class
        :return: If it worked
        """
        if isinstance(data, list) and not self.loaded:  # Received list of vals, convert to member dict
            counter = 0
            for i in self.sensors:
                self.sensors[i] = data[counter]
                # Replace following line with only updating time series of new sensor data
                self.time_series[i] = datetime.datetime.utcnow().timestamp()
                counter += 1
            return True
        else:  # Failed to load list arg or data already loaded
            return False

    def load_data_from_bytes(self, data: bytes) -> bool:
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
                try:
                    self.time_series[i] = loaded_data[counter]
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
        result = np.zeros(shape=(1, 40))
        counter = 0
        for i in self.sensors:
            result.put(counter, self.sensors[i])
            counter += 1
            result.put(counter, self.time_series[i])
            counter += 1
        print(result)
        return result.tobytes()


if __name__ == '__main__':
    print('Don\'t run me as main!')

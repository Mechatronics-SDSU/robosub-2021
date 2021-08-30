"""Contains class to configure ports as per architecture diagram, along with saving and loading.
"""

import json
import os


filename = 'src/utils/ip_config.json'


class IPConfig:
    """Class data for the IP configuration
    """
    def __init__(self, settings=None) -> None:
        if settings is None:
            settings = self.set_to_defaults()
        elif len(settings) != len(self.set_to_defaults()):
            settings = self.set_to_defaults()
        self.grpc_port = settings[0]
        self.logging_port = settings[1]
        self.video_port = settings[2]
        self.telemetry_port = settings[3]
        self.pilot_port = settings[4]

    @staticmethod
    def set_to_defaults() -> list:
        """Default ports
        """
        return [50052, 50002, 50001, 50003, 50004]

    def to_json(self) -> list:
        """Converts to json
        """
        return [self.grpc_port,
                self.logging_port,
                self.video_port,
                self.telemetry_port,
                self.pilot_port]


def load_config_from_file(fname) -> IPConfig:
    """Loads config given a file name.
    """
    try:
        with open(fname, 'rb') as f:
            config = json.load(f)
            ipc = IPConfig(settings=config)
            return ipc
    except FileNotFoundError:
        print('File doesn\'t exist.')


def save_config(config) -> None:
    """Saves config to file.
    """
    with open(filename, 'w+') as f:
        json.dump(config, f)

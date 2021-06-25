"""Contains class to configure ports as per architecture diagram, along with saving and loading.
"""

import pickle


filename = 'config.pickle'


class IPConfig:
    """Class data for the IP configuration
    """
    def __init__(self):
        # Command GRPC
        self.grpc_port = 50052
        # Sockets
        self.logging_port = 50002
        self.video_port = 50001
        self.telemetry_port = 50003
        self.pilot_port = 50004


def load_config():
    """Loads config from file.
    """
    with open(filename, 'rb') as f:
        config = pickle.load(f)
        return config


def save_config(config):
    """Saves config to file.
    """
    with open(filename, 'wb') as f:
        pickle.dump(config, f, protocol=pickle.HIGHEST_PROTOCOL)

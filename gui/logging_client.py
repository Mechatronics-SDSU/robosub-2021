"""Logging Client demo.
Waits for logging server to send bytes data, decodes, saves as its own log.
See logger.py for more information.
"""

import socket

from logger import LoggerClient

SERVER_PORT = 50002


def log_parse(input_data):
    """Logs sometimes arrive in >1 at a time.
    Parses them out and returns a list.
    :return: List of all logs.
    """
    input_data = bytes.decode(input_data, encoding='utf-8')
    result = []
    s = ''
    j = 0
    for i in range(len(input_data)):
        if (input_data[i] == '{') and (s == ''):
            j = i
            s = '{'
        elif (input_data[i] == '}') and (s == '{'):
            result.append(input_data[j+1:i-1])
            s = ''
    return result


def main():
    """Logging client driver code
    """
    lc = LoggerClient()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect(('192.168.0.133', SERVER_PORT))
        while True:
            data = s.recv(4096)
            print(data)
            # Parse logs
            log_list = log_parse(data)
            # Save the logs
            for i in range(len(log_list)):
                lc.logging_queue.append(log_list[i])
                lc.dequeue()


if __name__ == '__main__':
    main()

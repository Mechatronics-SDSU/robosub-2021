"""The logger file provides 2 classes: LoggerServer and LoggerClient.

LoggerServer is meant to be on one end of a communication pathway and LoggerClient is meant to be on the other.

These are not integrated into the logging_client and logging_server files because of both a design and organization
decision. This allows multiple logger servers to be instantiated from different sources and perhaps pipe logs
internally within the SUB to be sent to Intelligence.

As an example:
-Control subsystem hits a WARN case for SUB's battery current dropping below normal levels.
-Control has its OWN LoggerServer it writes its OWN logs to.
-Control sends these logs to Intelligence from Control's LoggerServer to Intelligence's LoggerClient.
-Intelligence loads messages from this LoggerClient into its own LoggerServer, which includes its own logs
and logs from other subsystems.
-Intelligence sends messages to HOST from its own LoggerServer, which has a LoggerClient.

Implementation will be up to whoever works with this on the SUB end and decides how logs
will be sent to Intelligence from other subsystems.
"""

import logging
import datetime


class LoggerServer:
    """
    :param save_logs: Whether to save logs to disk.
    :param level: Level at which to log information, using python's logging module.
    :param use_timestamp: Whether to include timestamps on logs.
    """
    def __init__(self, save_logs=True,
                 level=logging.INFO,
                 use_timestamp=True,
                 log_dest='system.log'):
        self._save = save_logs
        self._level = level
        self._timestamp = use_timestamp
        self.logging_queue = []
        self.log_dest = log_dest
        if self._save:
            logging.basicConfig(filename=self.log_dest, level=self._level)
        else:
            logging.basicConfig(level=self._level)
        self.log(prio=self._level,
                subsystem='System',
                message=str(datetime.datetime.now().strftime('[%Y/%m/%d]')) + 'Started NEW Logger Server Instance.')

    def log(self, prio, subsystem, message):
        """Calls python's logger and enqueues the log in the log queue for sending to HOST.
        :param prio: priority for logging.
        :param subsystem: subsystem doing the logging.
        :param message: log message.
        """
        ts = ''
        prio_str = ''
        if self._timestamp:
            ts = str(datetime.datetime.now().strftime('[%H:%M:%S]'))
        log = '[' + str(subsystem.strip()) + '] ' + ts + ': ' + str(message.strip())
        # PYTHON PLS ADD SWITCH CASE
        if prio == logging.DEBUG:
            logging.debug(log)
            prio_str = '[DEBUG] '
        elif prio == logging.INFO:
            logging.info(log)
            prio_str = '[INFO] '
        elif prio == logging.WARNING:
            logging.warning(log)
            prio_str = '[WARNING] '
        elif prio == logging.ERROR:
            logging.error(log)
            prio_str = '[ERROR] '
        elif prio == logging.CRITICAL:
            logging.critical(log)
            prio_str = '[CRITICAL] '
        self.logging_queue.append(('{' + prio_str + log + '}'))
        # print(self.logging_queue[len(self.logging_queue)-1])  # Testing print string

    def to_bytes(self):
        """Converts first log in the queue to a bytes object and dequeues.
        """
        if len(self.logging_queue) > 0:
            if isinstance(self.logging_queue[0], str):
                result = bytes(self.logging_queue[0], encoding='utf-8')
                self.logging_queue = self.logging_queue[1:]
                return result


class LoggerClient:
    """Receives logs from server.
    Logs are not written to this class, it only translates from bytes and saves if needed.
    """
    def __init__(self, save_logs=True):
        self._save = save_logs
        self._level = logging.DEBUG
        self._log_dest = 'system.log'
        self.logging_queue = []
        if self._save:
            logging.basicConfig(filename=self._log_dest, level=self._level)
        else:
            logging.basicConfig(level=self._level)

    @staticmethod
    def get_prio(log):
        """Parses the level of the log.
        :param log: Log string to parse.
        :return: level of log as defined in logging as a string.
        """
        if isinstance(log, str):
            found = ''
            index = 0
            counter = 0
            for i in log:
                if (i == '[') and (found == ''):
                    index = counter
                    found = '['
                elif (i == ']') and (found == '['):
                    return log[index+1:counter]
                counter += 1

    def dequeue(self):
        """Dequeues the first message in the logging queue after converting it from bytes.
        :return The string logged.
        """
        if len(self.logging_queue) > 0:
            log = self.logging_queue[0]
            prio = self.get_prio(log)
            if prio == 'DEBUG':
                if self._save:
                    logging.debug(log)

            elif prio == 'INFO':
                if self._save:
                    logging.info(log)

            elif prio == 'WARNING':
                if self._save:
                    logging.warning(log)

            elif prio == 'ERROR':
                if self._save:
                    logging.error(log)

            elif prio == 'CRITICAL':
                if self._save:
                    logging.critical(log)
            self.logging_queue = self.logging_queue[1:]
            return log


if __name__ == '__main__':
    print('Don\'t run me as main!')

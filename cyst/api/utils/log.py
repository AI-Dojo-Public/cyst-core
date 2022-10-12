import logging
import sys

from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter("[%(asctime)s] :: %(name)s — %(levelname)s :: %(message)s")
LOG_FILE = "cyst.log"


class SeverityFilter(logging.Filter):
    def __init__(self):
        super(SeverityFilter).__init__()

        self._severity_map = {
            "messaging": logging.DEBUG,
            "services.": logging.DEBUG
        }

    def filter(self, record: logging.LogRecord) -> int:  #MYPY: Wrong return type based on parent class
        # Filter by name
        for category in self._severity_map.items():
            if record.name.startswith(category[0]):
                if record.levelno >= category[1]:
                    return 1
                else:
                    return 0

        # Default case for unmatched names are governed by log's minimal severity
        return 1


def get_console_handler() -> logging.Handler:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler() -> logging.Handler:
    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name) -> logging.Logger:
    logger = logging.getLogger(logger_name)

    logger.setLevel(logging.DEBUG) # better to have too much log than not enough

    if not logger.hasHandlers():
        logger.addHandler(get_console_handler())
        # logger.addHandler(get_file_handler())
        logger.addFilter(SeverityFilter())

        logger.propagate = False

    return logger

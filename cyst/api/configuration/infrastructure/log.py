import logging

from dataclasses import dataclass, field
from enum import Enum, auto
from uuid import uuid4

from serde import serialize, coerce

from cyst.api.configuration.configuration import ConfigItem


class LogSource(Enum):
    """
    Categories of log sources.

    Possible values:
        :SYSTEM: Activities of the environment; set up, tear down, exception handling, etc.
        :MESSAGING: Logging of messages that are traversing the simulation.
        :SERVICE: Logging of active services' events.
        :MODEL: Logging of models' events.
    """
    SYSTEM = auto()
    MESSAGING = auto()
    SERVICE = auto()
    MODEL = auto()


class LogType(Enum):
    """
    Log entries structure.

    Possible values:
        :TEXT: Log entries are plain texts. One entry per line.
        :JSON: Log entries are JSON. The whole log is not JSON-compliant, because of missing top-level object.
    """
    TEXT = auto()
    JSON = auto()


@serialize(type_check=coerce)
@dataclass
class LogConfig(ConfigItem):
    """
    CYST provides what we feel are sensible defaults for logging and this configuration enables slight corrections of
    this default. The logging is built upon Python's logging framework. Each of log sources is assigned a named logger
    with the names 'system', 'messaging', 'service.', and 'model.' respectively.

    For full customization, you can disable a log by setting log_console and log_file options to False, and then you can
    use Python's logging facilities to set the system up to your liking.

    :param source: Source of the logs. While system and messaging logs will always work as expected, service and model
        logs require their authors to abide by a convention and use the logs named 'service.xxx' and 'model.xxx'.
    :type source: LogSource

    :param log_level: A level of messages to log. It is best to follow categories of Python's logging framework and use
        one of logging.(CRITICAL, ERROR, WARNING, INFO, DEBUG).
    :type log_level: int

    :param log_type: A type of logging to use. Mainly depends on whether you want a machine to process it or not.
    :type log_type: LogType

    :param log_console: Enable or disable logging to console.
    :type log_console: bool

    :param log_file: Enable or disable logging to file. If logging to file is enabled, file_path must be specified.
    :type log_file: bool

    :param file_path: A path to file that should be used for logging. If logging to file is not enabled, file is not
        opened/created.
    :type file_path: str

    """
    source: LogSource
    log_level: int
    log_type: LogType
    log_console: bool
    log_file: bool
    file_path: str = ""
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__log"
    id: str = ""


log_defaults = [
    LogConfig(
        source=LogSource.SYSTEM,
        log_level=logging.INFO,
        log_type=LogType.TEXT,
        log_console=True,
        log_file=True,
        file_path="log/cyst_system.log"
    ),
    LogConfig(
        source=LogSource.MESSAGING,
        log_level=logging.DEBUG,
        log_type=LogType.TEXT,
        log_console=True,
        log_file=True,
        file_path="log/cyst_messages.log"
    ),
    LogConfig(
        source=LogSource.SERVICE,
        log_level=logging.DEBUG,
        log_type=LogType.TEXT,
        log_console=True,
        log_file=True,
        file_path="log/cyst_service.log"
    ),
    LogConfig(
        source=LogSource.MODEL,
        log_level=logging.INFO,
        log_type=LogType.TEXT,
        log_console=True,
        log_file=False
    )
]

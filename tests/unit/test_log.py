import logging
import os.path
import unittest

from pathlib import Path
from time import sleep
from typing import List

from cyst.api.configuration.infrastructure.infrastructure import InfrastructureConfig
from cyst.api.configuration.infrastructure.log import LogSource, LogConfig, log_defaults

from cyst.api.environment.environment import Environment


class TestLog(unittest.TestCase):

    # Cleanup all the logs opened with previous environment initializations
    def setUp(self) -> None:
        loggers = [logging.getLogger()] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for logger in loggers:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()

    # Default init is only specific in that it creates a message file
    def test_0000_default_init(self) -> None:
        message_log = Path("cyst_messages.log")
        message_log.unlink(missing_ok=True)

        env = Environment.create().configure()
        env.control.commit()

        self.assertTrue(message_log.exists(), "cyst_messages.log created")

        logger = logging.getLogger("messaging")

        logger.debug("Test message to write")

        self.assertGreater(os.path.getsize("cyst_messages.log"), 0, "Message successfully written.")

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()

        message_log.unlink(missing_ok=True)

    def test_0001_disable_all_logs(self) -> None:
        defaults: List[LogConfig] = log_defaults.copy()
        for log in defaults:
            log.log_console = False
            log.log_file = False

        env = Environment.create().configure(InfrastructureConfig(log=defaults))

        logger = logging.getLogger("system")
        logger.info("If you see this, something is wrong")

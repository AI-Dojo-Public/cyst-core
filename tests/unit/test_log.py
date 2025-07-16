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
        env = Environment.create().configure()
        env.control.init()

        if env.infrastructure.runtime_configuration.run_id_log_suffix:
            message_log = Path(f"log/cyst_messages-{env.infrastructure.runtime_configuration.run_id}.log")
        else:
            message_log = Path("log/cyst_messages.log")

        env.control.commit()

        self.assertTrue(message_log.exists(), "cyst_messages.log created")

        logger = logging.getLogger("messaging")

        logger.debug("Test message to write")

        self.assertGreater(message_log.stat().st_size, 0, "Message successfully written.")

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()

        # Without suffix, this unlinks all logs. So, if you want to inspect test logs, you have to use log suffixes or
        # comment out the following line.
        message_log.unlink(missing_ok=True)

    def test_0001_disable_all_logs(self) -> None:
        defaults: List[LogConfig] = log_defaults.copy()
        for log in defaults:
            log.log_console = False
            log.log_file = False

        env = Environment.create().configure(InfrastructureConfig(log=defaults))
        env.control.init()

        logger = logging.getLogger("system")
        logger.info("If you see this, something is wrong")

        env.control.commit()

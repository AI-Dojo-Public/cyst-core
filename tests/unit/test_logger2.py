import unittest
from utils.logger import Log, Category
from environment.message import Request


class TestPolicy(unittest.TestCase):

    def test_logger(self):

        req = Request("1.2.3.4")
        req._src_ip = "4.3.2.1"

        req2 = Request("5.6.7.8")
        req2._src_ip = "8.7.6.5"

        console_logger = Log.get_logger("console-debug")
        console_logger.log("Console", Log.DEBUG)

        file_logger = Log.get_logger("file-info")
        file_logger.log(req, Log.INFO)

        file_logger = Log.get_logger("file-info.no-request")
        file_logger.log(req2, Log.INFO)


if __name__ == '__main__':
    unittest.main()

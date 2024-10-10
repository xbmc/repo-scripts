# -*- coding: utf-8 -*-

from bossanova808 import exception_logger
from resources.lib import cabertoss

if __name__ == "__main__":
    with exception_logger.log_exception():
        cabertoss.run()

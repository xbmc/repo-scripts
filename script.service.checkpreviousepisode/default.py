from resources.lib import check_previous_episode
import sys
from bossanova808 import exception_logger

if __name__ == "__main__":
    with exception_logger.log_exception():
        check_previous_episode.run(sys.argv)

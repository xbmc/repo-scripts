from bossanova808 import exception_logger
from resources.lib import unpause_jumpback

if __name__ == "__main__":
    with exception_logger.log_exception():
        unpause_jumpback.run()

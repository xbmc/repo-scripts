from bossanova808 import exception_logger
from resources.lib import playback_resumer

if __name__ == "__main__":
    with exception_logger.log_exception():
        playback_resumer.run()

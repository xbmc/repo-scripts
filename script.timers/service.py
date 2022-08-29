from resources.lib.timer.scheduler import Scheduler
from resources.lib.utils.system_utils import set_windows_unlock


def run() -> None:

    scheduler = Scheduler()
    try:
        scheduler.start()

    finally:
        scheduler.reset_powermanagement_displaysoff()
        set_windows_unlock(False)

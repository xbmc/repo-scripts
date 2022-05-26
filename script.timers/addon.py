import migration
from resources.lib.timer.scheduler import Scheduler
from resources.lib.utils.system_utils import set_windows_unlock

if __name__ == "__main__":

    migration.migrate()

    scheduler = Scheduler()

    try:
        scheduler.start()

    finally:
        scheduler.resetPowermanagementDisplaysoff()
        set_windows_unlock(False)

import migration
from resources.lib.timer import scheduler
from resources.lib.utils import system_utils

if __name__ == "__main__":

    migration.migrate()

    scheduler = scheduler.Scheduler()

    try:
        scheduler.start()

    finally:
        scheduler.reset_powermanagement_displaysoff()
        system_utils.set_windows_unlock(False)

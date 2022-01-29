import xbmcaddon

from resources.lib.timer import migration, scheduler, util

if __name__ == "__main__":

    util.prevent_strptime_error()

    migration.migrate()

    scheduler = scheduler.Scheduler(xbmcaddon.Addon())

    try:
        scheduler.start()

    finally:
        scheduler.reset_powermanagement_displaysoff()
        util.set_windows_unlock(False)

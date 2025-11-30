import xbmc
import xbmcaddon
from datetime import datetime, timedelta
from resources.lib.rating_updater import RatingUpdater
from resources.lib.logger import Logger

class RatingUpdaterService(xbmc.Monitor):
    def __init__(self):
        super(RatingUpdaterService, self).__init__()
        self.addon = xbmcaddon.Addon()
        self.logger = Logger()
        self.updater = RatingUpdater()

    def is_first_run(self):
        """Check if this is the first time the script is running"""
        last_completion = self.addon.getSetting('last_completion')
        return last_completion == ''

    def should_run_update(self):
        if self.is_first_run():
            return True
        
        try:
            last_completion = self.addon.getSetting('last_completion')
            last_completion_date = datetime.fromisoformat(last_completion)
            interval_days = self.addon.getSettingInt('update_interval')
            next_run = last_completion_date + timedelta(days=interval_days)
            
            return datetime.now() >= next_run
        except ValueError:
            return True

    def save_completion_time(self):
        completion_time = datetime.now().isoformat()
        self.addon.setSetting('last_completion', completion_time)

    def run(self):
        self.logger.info("Get Latest Rating Service Started")
        
        if self.is_first_run():
            self.logger.info("First time running - performing initial update")
        
        if self.should_run_update():
            self.logger.info("Starting scheduled update")
            self.updater.update_library_ratings()
            self.save_completion_time()
            self.logger.info("Update completed successfully")
        else:
            self.logger.debug("Skipping update - next update not due yet")
        
        self.logger.info("Rating Updater Service Stopped")

if __name__ == '__main__':
    service = RatingUpdaterService()
    service.run() 
import os
import time
import scraper
from ... import util
from .. import _scrapers


class Trailer(_scrapers.Trailer):
    @property
    def ID(self):
        return 'stereoscopynews:{0}'.format(self.data['ID'])

    @property
    def title(self):
        return self.data.get('title')

    @property
    def is3D(self):
        return True

    def getPlayableURL(self, res='720p'):
        return 'plugin://plugin.video.youtube/play/?video_id={0}'.format(self.data['ID'])


class StereoscopyNewsTrailerScraper(_scrapers.Scraper):
    LAST_UPDATE_FILE = os.path.join(util.STORAGE_PATH, 'stereoscopynewst.last')

    def __init__(self):
        self.loadTimes()

    def getTrailers(self):
        if self.allIsDue():
            util.DEBUG_LOG(' - Fetching all trailers')
            return [Trailer(t) for t in scraper.getTrailers()]

        return []

    @staticmethod
    def getPlayableURL(ID, res='720p', url=None):
        return 'plugin://plugin.video.youtube/play/?video_id={0}'.format(ID)

    def loadTimes(self):
        self.lastAllUpdate = 0
        self.lastRecentUpdate = 0
        if not os.path.exists(self.LAST_UPDATE_FILE):
            return
        try:
            with open(self.LAST_UPDATE_FILE, 'r') as f:
                self.lastAllUpdate, self.lastRecentUpdate = [int(x) for x in f.read().splitlines()[:2]]
        except:
            util.ERROR()

    def saveTimes(self):
        with open(self.LAST_UPDATE_FILE, 'w') as f:
            f.write('{0}\n{1}'.format(int(self.lastAllUpdate), int(self.lastRecentUpdate)))

    def allIsDue(self):
        if time.time() - self.lastAllUpdate > 2592000:  # One month
            self.lastAllUpdate = time.time()
            self.saveTimes()
            return True
        return False

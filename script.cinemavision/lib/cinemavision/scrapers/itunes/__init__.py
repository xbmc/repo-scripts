import scraper
import os
import re
import time
import datetime
from ... import ratings
from ... import util
from .. import _scrapers


class Trailer(_scrapers.Trailer):
    def __init__(self, data):
        self.data = data
        if self.data.get('rating', '').lower().startswith('not'):
            self.data['rating'] = 'NR'
        self.rating = ratings.getRating('MPAA', self.data.get('mpaa', ''))

    @property
    def ID(self):
        return 'itunes:{0}.{1}'.format(self.data['movie_id'], self.data['location'])

    @property
    def title(self):
        return self.data['title']

    @property
    def thumb(self):
        return self.data['poster']

    @property
    def genres(self):
        return re.split(' and |, ', self.data.get('genre', ''))

    @property
    def userAgent(self):
        return scraper.BROWSER_UA

    @property
    def release(self):
        return self.data.get('releasedatetime', datetime.date(1900, 1, 1))

    def getStaticURL(self):
        return None

    def getPlayableURL(self, res='720p'):
        try:
            return self._getPlayableURL(res)
        except:
            import traceback
            traceback.print_exc()

        return None

    def _getPlayableURL(self, res='720p'):
        return ItunesTrailerScraper.getPlayableURL(self.data['location'], res)


class ItunesTrailerScraper(_scrapers.Scraper):
    LAST_UPDATE_FILE = os.path.join(util.STORAGE_PATH, 'itunes.last')

    RES = {
        '480p': 'sd',
        '720p': 'hd720',
        '1080p': 'hd1080',
    }

    def __init__(self):
        self.loadTimes()

    @staticmethod
    def getPlayableURL(ID, res=None, url=None):
        res = ItunesTrailerScraper.RES.get(res, 'hd720p')

        ts = scraper.Scraper()
        id_location = ID.split('.', 1)
        all_ = [t for t in ts.get_trailers(id_location[-1], id_location[0]) if t]

        if not all_:
            return None

        trailers = [t for t in all_ if t['title'] == 'Trailer']

        url = None
        if trailers:
            try:
                version = [v for v in trailers if any(res in u for u in v['streams'])][0]
                if version:
                    url = [u for u in version['streams'] if res in u][0]
            except:
                import traceback
                traceback.print_exc()

        if not url:
            try:
                streams = all_[0]['streams']
                url = streams.get(res, streams.get('hd720', streams.get('sd')))
            except:
                import traceback
                traceback.print_exc()

        url = re.sub(r'(480p|720p|1080p)', r'h\1', url)

        return url

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

    def recentIsDue(self):
        if time.time() - self.lastRecentUpdate > 86400:  # One day
            self.lastRecentUpdate = time.time()
            self.saveTimes()
            return True
        return False

    def getTrailers(self):
        ms = scraper.Scraper()
        if self.allIsDue():
            util.DEBUG_LOG('    - Fetching all trailers')
            return [Trailer(t) for t in ms.get_all_movies(None)]

        return []

    def updateTrailers(self):
        ms = scraper.Scraper()
        if self.recentIsDue():
            util.DEBUG_LOG('    - Fetching recent trailers')
            return [Trailer(t) for t in ms.get_most_recent_movies(None)]

        return []

    def convertURL(self, url, res):
        # Not currently used
        repl = None
        for r in ('h480p', 'h720p', 'h1080p'):
            if r in url:
                repl = r
                break
        if not repl:
            return url

        return url.replace(repl, 'h{0}'.format(res))

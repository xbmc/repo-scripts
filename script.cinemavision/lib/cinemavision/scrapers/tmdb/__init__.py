import scraper
import os
import re
import time
import datetime
from ... import ratings
from ... import util
from .. import _scrapers

GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western"
}

class Trailer(_scrapers.Trailer):
    def __init__(self, data):
        self.data = data

    @property
    def ID(self):
        return 'tmdb:{0}'.format(self.data['id'])

    @property
    def title(self):
        return self.data['title']

    @property
    def thumb(self):
        return 'https://image.tmdb.org/t/p/w500' + self.data['poster_path']

    @property
    def genres(self):
        if 'genre_ids' in self.data:
            return [GENRES[g] for g in self.data['genre_ids'] if GENRES[g]]
        elif 'genres' in self.data:
            return [g['name'] for g in self.data['genres']]

        return []

    @property
    def rating(self):
        if hasattr(self, '_rating'):
            return self._rating

        if not 'release_dates' in self.data:
            return None

        us = [u for u in self.data['release_dates']['results'] if u.get('iso_3166_1') == 'US']
        if not us:
            return ratings.getRating('MPAA', 'NR')

        withRatings = [r['certification'] for r in us[0]['release_dates'] if r.get('certification')]
        if not withRatings:
            return ratings.getRating('MPAA', 'NR')

        self._rating = ratings.getRating('MPAA', withRatings[0])
        return self._rating

    @property
    def userAgent(self):
        return ''

    @property
    def release(self):
        try:
            dateSplit = [int(d) for d in self.data.get('release_date', '1900-01-01').split('-')]
            return datetime.datetime(*dateSplit)
        except:
            import traceback
            traceback.print_exc()

        return datetime.datetime(1900, 1, 1)

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
        return TMDBTrailerScraper.getPlayableURL(self.ID, res)


class TMDBTrailerScraper(_scrapers.Scraper):
    ONLY_KEEP_VERIFIED = False
    REMOVE_DAYS_OLD = 120
    LAST_UPDATE_FILE = os.path.join(util.STORAGE_PATH, 'tmdb.last')

    RES = {
        '480p': 480,
        '720p': 720,
        '1080p': 1080,
    }

    def __init__(self):
        self.loadTimes()

    @staticmethod
    def getPlayableURL(ID, res=None, url=None):
        res = TMDBTrailerScraper.RES.get(res, 720)

        ts = scraper.Scraper()

        details = ts.getDetails(ID)

        if details is None:
            return ''

        videos = details.get('videos')

        if not videos:
            return ''

        trailers = [t for t in videos['results'] if t['type'] == 'Trailer']

        url = None
        if not trailers:
            return ''

        trailerID = ''
        try:
            trailerID = [t['key'] for t in trailers if t['size'] == res][0]
        except IndexError:
            pass
        except:
            import traceback
            traceback.print_exc()
            return ''

        if not trailerID:
            trailerID = trailers[0]['key']

        return 'plugin://plugin.video.youtube/play/?video_id={id}'.format(id=trailerID)

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
        if time.time() - self.lastAllUpdate > 21600:  # 6 Hours
            self.lastAllUpdate = time.time()
            self.saveTimes()
            return True
        return False

    def recentIsDue(self):
        if time.time() - self.lastRecentUpdate > 21600:  # 6 Hours
            self.lastRecentUpdate = time.time()
            self.saveTimes()
            return True
        return False

    def getTrailers(self):
        ms = scraper.Scraper()
        if self.allIsDue():
            util.DEBUG_LOG(' - Fetching all trailers')
            return [Trailer(t) for t in ms.getTrailers()]

        return []

    def updateTrailers(self):
        return self.getTrailers()

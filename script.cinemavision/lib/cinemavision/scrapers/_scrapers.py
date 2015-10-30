import datetime
from .. import ratings

CONTENT_PATH = None


class Trailer:
    def __init__(self, data):
        self.data = data

    @property
    def ID(self):
        return ''

    @property
    def title(self):
        return ''

    @property
    def thumb(self):
        return ''

    @property
    def genres(self):
        return []

    @property
    def rating(self):
        if not hasattr(self, '_rating'):
            self._rating = ratings.getRating(self.data.get('ratingFormat', 'MPAA'), self.data.get('rating', 'NR'))
        return self._rating

    @property
    def fullRating(self):
        return '{0}:{1}'.format(self.ratingFormat, self.rating)

    @property
    def userAgent(self):
        return ''

    @property
    def release(self):
        return datetime.date(1900, 1, 1)

    @property
    def is3D(self):
        return False

    @property
    def watched(self):
        return False

    def getStaticURL(self):
        return None

    def getPlayableURL(self, res='720p'):
        return ''


class Scraper:
    @staticmethod
    def getPlayableURL(ID, res='720p', url=None):
        return url

    def getTrailers(self):
        return []

    def updateTrailers(self):
        return []

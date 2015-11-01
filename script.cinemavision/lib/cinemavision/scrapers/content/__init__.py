import scraper
from ... import util
from .. import _scrapers


class Trailer(_scrapers.Trailer):
    def __init__(self, data):
        _scrapers.Trailer.__init__(self, data)
        self._is3D = util.pathIs3D(self.data.get('url', ''))

    @property
    def ID(self):
        return 'content:{0}'.format(self.data['ID'])

    @property
    def title(self):
        return self.data.get('title', 'ERROR_NO_TITLE')

    @property
    def is3D(self):
        return self._is3D

    def getPlayableURL(self, res='720p'):
        return 'plugin://plugin.video.youtube/play/?video_id={0}'.format(self.data['ID'])


class ContentTrailerScraper(_scrapers.Scraper):
    def getTrailers(self):
        return [Trailer(t) for t in scraper.getTrailers()]

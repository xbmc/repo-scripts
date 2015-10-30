import datetime
from lib.kodijsonrpc import rpc
from lib import kodiutil


def getTrailers():
    skipYouTube = kodiutil.getSetting('scraper.trailers.KodiDB.skipYouTube', False)
    markWatched = kodiutil.getSetting('scraper.trailers.KodiDB.markWatched', False)

    for m in rpc.VideoLibrary.GetMovies(properties=['trailer', 'mpaa', 'genre', 'year', 'playcount']).get('movies', []):
        trailer = m.get('trailer')

        if not trailer:
            continue

        if skipYouTube and trailer.startswith('plugin://'):
            continue

        yield {
            'ID': m['movieid'],
            'url': trailer,
            'rating': m['mpaa'],
            'genres': m['genre'],
            'title': m['label'],
            'release': datetime.datetime(year=m.get('year') or 1900, month=1, day=1),
            'watched': markWatched and m.get('playcount', 0)
        }

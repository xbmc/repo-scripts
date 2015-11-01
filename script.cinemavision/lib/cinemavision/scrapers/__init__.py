import _scrapers

_SOURCES = {
    'itunes': 'iTunes',
    'kodidb': 'kodiDB',
    'stereoscopynews': 'StereoscopyNews',
    'content': 'Content'
}


def getScraper(source=None):
    source = _SOURCES.get(source.lower().strip())

    if source == 'iTunes':
        import itunes
        return itunes.ItunesTrailerScraper()
    elif source == 'kodiDB':
        import kodidb
        return kodidb.KodiDBTrailerScraper()
    elif source == 'StereoscopyNews':
        import stereoscopynews
        return stereoscopynews.StereoscopyNewsTrailerScraper()
    elif source == 'Content':
        import content
        return content.ContentTrailerScraper()
    return None


def getTrailers(source=None):
    scraper = getScraper(source)
    if not scraper:
        return None

    return scraper.getTrailers()


def updateTrailers(source=None):
    scraper = getScraper(source)
    if not scraper:
        return None

    return scraper.updateTrailers()


def getPlayableURL(ID, quality=None, source=None, url=None):
    scraper = getScraper(source)
    if not scraper:
        return None

    return scraper.getPlayableURL(ID, quality, url)


def setContentPath(path):
    _scrapers.CONTENT_PATH = path

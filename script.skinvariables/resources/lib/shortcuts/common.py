import re


IMAGE_REGEX = r'image://(.*)/'
ARTWORK_PREFERENCE = ['poster', 'thumb', 'icon', 'landscape', 'fanart']


class GetDirectoryCommon():
    def __init__(self, path, library='video', dbtype='video', definitions=None, target=None):
        self.path = path
        self.library = library
        self.dbtype = dbtype
        self.target = target
        self.definitions = definitions or {}

    @property
    def directory(self):
        try:
            return self._directory
        except AttributeError:
            self._directory = self.get_directory()
            return self._directory

    @property
    def items(self):
        try:
            return self._items
        except AttributeError:
            self._items = self.get_items()
            return self._items

    def get_artwork_fallback(self, listitem):
        artwork = listitem.artwork
        artwork_types = ARTWORK_PREFERENCE
        for a in artwork_types:
            if not artwork.get(a):
                continue
            artwork['thumb'] = artwork[a]
            break
        thumb = ''
        try:
            thumb = artwork.get('thumb') or ''
            if thumb.startswith('image://Default'):
                regex = re.search(IMAGE_REGEX, thumb)
                thumb = regex.group(1) if regex else thumb
                thumb = self.definitions.setdefault('icons', {}).get(thumb) or thumb
                thumb = f'special://skin/media/{thumb}' if thumb.startswith('Default') else thumb
            thumb = thumb or 'special://skin/media/DefaultFolder.png'
        except KeyError:
            thumb = 'special://skin/media/DefaultFolder.png'
        thumb = self.definitions.setdefault('icons', {}).get(thumb.replace('special://skin/media/', '')) or thumb
        artwork['thumb'] = thumb
        return artwork

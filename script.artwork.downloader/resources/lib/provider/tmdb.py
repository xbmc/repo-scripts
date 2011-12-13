from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import _log as log
from resources.lib import language
from elementtree import ElementTree as ET

class TMDBProvider(BaseProvider):

    def __init__(self):
        self.name = 'TMDB'
        self.api_key = '4be68d7eab1fbd1b6fd8a3b80a65a95e'
        self.api_limits = True
        self.url = "http://api.themoviedb.org/2.1/Movie.getImages/" + language.get_abbrev() + "/xml/%s/%s"

    def get_image_list(self, media_id):
        xml_url = self.url % (self.api_key, media_id)
        log('API: %s ' % xml_url)
        image_list = []
        data = self.get_xml(xml_url)
        tree = ET.fromstring(data)
        tree = tree.findall('movies')[0]
        try:
            tree = tree.findall('movie')[0]
        except IndexError:
            raise ItemNotFoundError(media_id)
        else:
            tree = tree.findall('images')[0]
            for imagetype in ['poster', 'backdrop']:
                for image in tree.findall(imagetype):
                    for sizes in image:
                        info = {}
                        info['id'] = image.get('id')
                        info['type'] = ''
                        if imagetype == 'backdrop' and sizes.get('size') == 'original':
                            info['type'] = 'fanart'
                        elif imagetype == 'backdrop' and sizes.get('size') == 'poster':
                            info['type'] = 'thumb'
                        elif imagetype == 'poster' and sizes.get('size') == 'original':
                            info['type'] = 'poster'
                        if not info['type'] == '' and sizes.get('size') == 'thumb':
                            info['preview'] = sizes.get('url')
                        info['url'] = sizes.get('url')
                        info['height'] = int(sizes.get('height'))
                        info['width'] = int(sizes.get('width'))
                        if info:
                            image_list.append(info)
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                return image_list
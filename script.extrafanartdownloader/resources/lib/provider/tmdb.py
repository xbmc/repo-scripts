from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import _log as log
from resources.lib import language

from elementtree import ElementTree as ET

class TMDBProvider(BaseProvider):
    """
    Setup provider for TheMovieDB.org
    """
    def __init__(self):
        self.name = 'TMDB'
        self.api_key = '4be68d7eab1fbd1b6fd8a3b80a65a95e'
        self.api_limits = True
        self.url = "http://api.themoviedb.org/2.1/Movie.imdbLookup/" + language.get_abbrev() + "/xml/%s/%s"
        
        
    def get_filename(self, imageid):
        filename = imageid + '.jpg'
        return filename
        
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
            for image in tree.findall('image'):
                info = {}
                if image.get('type') == 'backdrop' and image.get('url'):
                    info['size'] = image.get('size')
                    info['id'] = image.get('id')
                    info['url'] = image.get('url')
                    info['height'] = int(image.get('height'))
                    info['width'] = int(image.get('width'))
                if info:            
                    image_list.append(info) 
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                return image_list 

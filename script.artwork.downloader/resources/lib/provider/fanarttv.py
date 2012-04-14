#import modules
import sys
import urllib
import xbmc
### import libraries
from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import *
from elementtree import ElementTree as ET
from operator import itemgetter
from resources.lib.language import *

### get addon info
__localize__    = ( sys.modules[ '__main__' ].__localize__ )

API_KEY = '586118be1ac673f74963cc284d46bd8e'
IMAGE_TYPES = ['clearlogo', 'clearart', 'tvthumb', 'seasonthumb', 'characterart','movielogo', 'movieart', 'moviedisc']

class FTV_TVProvider():

    def __init__(self):
        self.name = 'fanart.tv - TV API'
        self.url = 'http://fanart.tv/webservice/series/%s/%s/json/all/1/2'

    def get_image_list(self, media_id):
        data = get_json(self.url % (API_KEY,media_id))
        image_list = []
        if data == 'Empty' or not data:
            return image_list
        else:
            # split 'name' and 'data'
            for title, value in data.iteritems():
                for art in IMAGE_TYPES:
                    if value.has_key(art):
                        for item in value[art]:
                            # Create GUI info tag
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), get_language(item.get('lang')).capitalize())
                            if item.get('season'):
                                generalinfo += '%s: %s  |  ' %( __localize__(32144), item.get('season'))
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), item.get('likes'))
                            # Fill list
                            image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                               'preview': item.get('url') + '/preview',
                                               'id': item.get('id'),
                                               'type': art,
                                               'season': item.get('season','n/a'),
                                               'language': item.get('lang'),
                                               'votes': item.get('likes'),
                                               'generalinfo': generalinfo})
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('language'))
                return image_list
            
class FTV_MovieProvider():

    def __init__(self):
        self.name = 'fanart.tv - Movie API'
        self.url = 'http://fanart.tv/webservice/movie/%s/%s/json/all/1/2/'
        

    def get_image_list(self, media_id):
        data = get_json(self.url %(API_KEY, media_id))
        image_list = []
        if data == 'Empty' or not data:
            return image_list
        else:
            # split 'name' and 'data'
            for title, value in data.iteritems():
                for art in IMAGE_TYPES:
                    if value.has_key(art):
                        for item in value[art]:
                            # Check on what type and use the general tag
                            arttypes = {'movielogo': 'clearlogo',
                                        'moviedisc': 'discart',
                                        'movieart': 'clearart'}
                            type = arttypes[art]
                            # Create GUI info tag
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), get_language(item.get('lang')).capitalize())
                            if item.get('disc_type'):
                                generalinfo += '%s: %s (%s)  |  ' %( __localize__(32146), item.get('disc'), item.get('disc_type'))
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), item.get('likes'))
                            # Fill list
                            image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                               'preview': item.get('url') + '/preview',
                                               'id': item.get('id'),
                                               'type': type,
                                               'season': item.get('season','n/a'),
                                               'language': item.get('lang'),
                                               'votes': item.get('likes'),
                                               'disctype': item.get('disc_type','n/a'),
                                               'discnumber': item.get('disc','n/a'),
                                               'generalinfo': generalinfo})
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('language'))
                return image_list
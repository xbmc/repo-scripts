### import libraries
from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import _log as log
from resources.lib.utils import _get_xml as get_xml
from elementtree import ElementTree as ET
import urllib

class FTV_TVProvider():

    def __init__(self):
        self.name = 'fanart.tv - TV API'
        self.api_key = '586118be1ac673f74963cc284d46bd8e'
        #self.url = "http://fanart.tv/webservice/series/%s/%s/xml/all/1/2"
        self.url = 'http://fanart.tv/api/fanart.php?v=4&id=%s'
        self.imagetypes = ['clearlogo', 'clearart', 'tvthumb', 'seasonthumb', 'characterart']

    def get_image_list(self, media_id):
        #xml_url = self.url % (self.api_key,media_id)
        xml_url = self.url % (media_id)
        log('API:               %s ' % xml_url)
        image_list = []
        data = get_xml(xml_url)
        tree = ET.fromstring(data)
        for imagetype in self.imagetypes:
            imageroot = imagetype + 's'
            for images in tree.findall(imageroot):
                for image in images:
                    info = {}
                    info['id'] = image.get('id')
                    info['url'] = urllib.quote(image.get('url'), ':/')
                    info['preview'] = info['url']
                    info['type'] = [imagetype]
                    info['rating'] = 'n/a'
                    info['language'] = 'n/a'
                    '''
                    info['preview'] = urllib.quote(image.get('preview'), ':/')
                    info['language'] = image.get('lang')
                    info['likes'] = image.get('likes')
                    if imagetype == 'seasonthumb':
                        seasonxx = "%.2d" % int(image.findtext('season')) #ouput is double digit int
                        if seasonxx == '00':
                            info['season'] = '-specials'
                        else:
                            info['season'] = str(seasonxx)
                        info['season'] = "%.2d" % int(image.get('season')) #ouput is double digit int
                    else:
                        info['season'] = 'NA'
                    info['generalinfo'] = 'Language: %s , Likes: %s   ' %(info['language'], info['likes'])
                    '''
                    # Create Gui string to display
                    info['generalinfo'] = 'Language: %s  |  Rating: %s   ' %(info['language'], info['rating'])
                    if info:
                        image_list.append(info)
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            return image_list


class FTV_MovieProvider():

    def __init__(self):
        self.name = 'fanart.tv - Movie API'
        self.api_key = '586118be1ac673f74963cc284d46bd8e'
        self.url = "http://fanart.tv/webservice/movie/%s/%s/xml/all/1/2/"
        self.imagetypes = ['clearlogo', 'clearart', 'cdart']

    def get_image_list(self, media_id):
        xml_url = self.url % (self.api_key,media_id)
        log('API: %s ' % xml_url)
        image_list = []
        data = get_xml(xml_url)
        tree = ET.fromstring(data)
        for imagetype in self.imagetypes:
            imageroot = imagetype + 's'
            for images in tree.findall(imageroot):
                for image in images:
                    info = {}
                    info['id'] = image.get('id')
                    info['url'] = urllib.quote(image.get('url'), ':/')
                    info['preview'] = urllib.quote(image.get('preview'), ':/')
                    info['type'] = imagetype
                    info['language'] = image.get('lang')
                    info['likes'] = image.get('likes')
                    # Create Gui string to display
                    info['generalinfo'] = 'Language: %s  |  Likes: %s   ' %(info['language'], info['likes'])
                    if info:            
                        image_list.append(info)
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            return image_list

from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import _log as log
from resources.lib import language

from elementtree import ElementTree as ET

class FTV_TVProvider(BaseProvider):

    def __init__(self):
        self.name = 'fanart.tv - TV API'
        self.url = 'http://fanart.tv/api/fanart.php?v=4&id=%s'
        self.imagetypes = ['clearlogo', 'clearart', 'tvthumb', 'seasonthumb', 'characterart']
    
        
    def get_image_list(self, media_id):
        xml_url = self.url % (media_id)
        log('API: %s ' % xml_url)
        image_list = []
        data = self.get_xml(xml_url)
        tree = ET.fromstring(data)
        for imagetype in self.imagetypes:
            imageroot = imagetype + 's'
            for images in tree.findall(imageroot):
                for image in images:
                    info = {}
                    info['url'] = image.get('url')
                    info['id'] = image.get('id')
                    info['type'] = imagetype
                    '''
                    Disabled seasonthumbs because there's now way of telling to what season or thumbset it belongs.
                    Needs to be fixed in the API first.
                    
                    if imagetype == 'seasonthumb':
                        try:
                            x,y = info['url'].split('(')
                            y,z = str(y).split(')')
                            info['season'] = "%.2d" % int(str(y)) #ouput is double digit int
                        except:
                            log('Failed retrieving season number')
                            info['season'] = ''
                    else: info['season'] = ''
                    '''
                    
                    if info:            
                        image_list.append(info)
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            return image_list 
        
class FTV_MovieProvider(BaseProvider):
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'fanart.tv - Music API'
        self.url = 'http://fanart.tv/api/fanart.php?id=%s'
        
class FTV_MusicProvider(BaseProvider):
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'fanart.tv - Music API'
        self.url = 'http://fanart.tv/api/music.php?id=%s&type=background'

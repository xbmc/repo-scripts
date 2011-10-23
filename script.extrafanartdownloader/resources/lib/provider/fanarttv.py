from resources.lib.provider.base import BaseProvider
#from script_exceptions import NoFanartError
#from utils import _log as log

#import ElementTree as ET

class FTVProvider(BaseProvider):
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'fanart.tv - TV API'
        self.url = 'http://fanart.tv/api/fanart.php?id=%s&type=tvthumb'

class FTVMusicProvider(BaseProvider):
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'fanart.tv - Music API'
        self.url = 'http://fanart.tv/api/music.php?id=%s&type=background'
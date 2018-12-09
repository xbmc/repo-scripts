import xbmc
import resources.lib.utils as utils
from resources.lib.api import Api
from resources.lib.developer import Developer


# service class for playback monitoring
class Player(xbmc.Player):
    def __init__(self):
        self.api = Api()
        self.developer = Developer()
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        # Will be called when kodi starts playing a file
        self.api.reset_addon_data()
        if utils.settings("developerMode") == "true":
            self.developer.developer_play_back()

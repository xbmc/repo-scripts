import xbmc
import resources.lib.utils as utils
from resources.lib.api import Api
from resources.lib.developer import Developer
from resources.lib.state import State


# service class for playback monitoring
class Player(xbmc.Player):
    last_file = None
    track = False

    def __init__(self):
        self.api = Api()
        self.state = State()
        self.developer = Developer()
        xbmc.Player.__init__(self)

    def set_last_file(self, file):
        self.state.last_file = file

    def get_last_file(self):
        return self.state.last_file

    def is_tracking(self):
        return self.state.track

    def disable_tracking(self):
        self.state.track = False

    def onPlayBackStarted(self):
        # Will be called when kodi starts playing a file
        xbmc.sleep(5000) # Delay for slower devices, should really use onAVStarted for Leia
        self.state.track = True
        if utils.settings("developerMode") == "true":
            self.developer.developer_play_back()

    def onPlayBackPaused(self):
        self.state.pause = True

    def onPlayBackResumed(self):
        self.state.pause = False

    def onPlayBackStopped(self):
        # Will be called when user stops playing a file.
        self.api.reset_addon_data()
        self.state =State() # reset state

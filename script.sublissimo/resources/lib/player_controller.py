import xbmc

from .play_along_file import PlayAlongFile
from .sync_wizard import SyncWizard
from .sync_by_frame_rate import SyncWizardFrameRate

class SearchFrameRate(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)
        self.frame_rate = 25

    def get_frame_rate(self):
        xbmc.sleep(1000)
        self.frame_rate = xbmc.getInfoLabel('Player.Process(VideoFPS)')
        self.stop()
        return float(self.frame_rate)

    def get_frame_rate_from_playing_file(self):
        self.frame_rate = xbmc.getInfoLabel('Player.Process(VideoFPS)')
        return float(self.frame_rate)

class PlayerInstance:
    def __init__(self):
        self.instances = []
        self.in_use = True

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(PlayerInstance, cls).__new__(cls)
        return cls.instance

    def deactivate(self):
        self.in_use = False
        for instance in self.instances:
            instance.proper_exit = True

    def request(self, value):
        types = {"playalongfile": PlayAlongFile,
                 "syncwizard": SyncWizard,
                 "syncbyframerate": SyncWizardFrameRate}
        new_obj = types[value]()
        self.instances.append(new_obj)
        self.in_use = True
        return new_obj

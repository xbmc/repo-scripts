__author__ = 'twi'

import tempfile
import os

settings = dict()
strings = dict()

class Addon:
    def __init__(self, id):
        self.id = id

    def getAddonInfo(self, id):
        if(id.lower() == 'profile'): # Profile path
            dir = os.path.join(tempfile.gettempdir(), self.id)
            if(not os.path.isdir(dir)):
                os.makedirs(dir)
            return dir

    def getLocalizedString(self, id):
        if strings.has_key(id):
            return strings[id]
        else:
            return "localizedString_%d" % id

    def getSetting(self, key):
        return settings[key]

    def setSetting(self, key, value):
        settings[key] = value
  
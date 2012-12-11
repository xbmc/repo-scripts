import xbmc
import xbmcaddon
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer
    
__addon_id__= 'service.libraryautoupdate'
__Addon = xbmcaddon.Addon(__addon_id__)

cache = StorageServer.StorageServer(__addon_id__,24)

def data_dir():
    return __Addon.getAddonInfo('profile')

def addon_dir():
    return __Addon.getAddonInfo('path')

def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(encode(__addon_id__ + ": " + message),level=loglevel)

def showNotification(title,message):
    xbmc.executebuiltin("Notification(" + encode(title) + "," + encode(message) + ",4000," + xbmc.translatePath(__Addon.getAddonInfo('path') + "/resources/images/clock.png") + ")")

def setSetting(name,value):
    __Addon.setSetting(name,value)

def setCache(name,value):
    cache.set(name,value)

def getSetting(name):
    return __Addon.getSetting(name)

def getCache(name):
    return cache.get(name)
    
def getString(string_id):
    return __Addon.getLocalizedString(string_id)

def encode(string):
    return string.encode('UTF-8','replace')

import xbmc
import xbmcaddon

if __name__ == "__main__":
    addon = xbmcaddon.Addon()
    xbmc.executebuiltin("Addon.OpenSettings(%s)" % addon.getAddonInfo('id'))

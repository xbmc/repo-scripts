import xbmc
import xbmcaddon
import xbmcgui
addon_id = "service.libraryautoupdate"
Addon = xbmcaddon.Addon(addon_id)

#show the disclaimer
xbmcgui.Dialog().ok(Addon.getLocalizedString(30018),"",Addon.getLocalizedString(30019),Addon.getLocalizedString(30020))

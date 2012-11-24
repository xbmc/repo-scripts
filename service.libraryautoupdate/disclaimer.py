import xbmc
import xbmcaddon
import xbmcgui
addon_id = "service.libraryautoupdate"
Addon = xbmcaddon.Addon(addon_id)

#show the disclaimer
xbmcgui.Dialog().ok(Addon.getLocalizedString(30031),"",Addon.getLocalizedString(30032),Addon.getLocalizedString(30033))

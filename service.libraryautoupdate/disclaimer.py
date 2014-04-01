import xbmcgui
import resources.lib.utils as utils

#show the disclaimer
xbmcgui.Dialog().ok(utils.getString(30031),"",utils.getString(30032),utils.getString(30033))

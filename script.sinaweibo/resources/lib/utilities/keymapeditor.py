import xbmc
import xbmcgui
import traceback
from resources.lib.utilities.common_addon import *


### Key mapp
def run():
    try:
        xbmc.executebuiltin("ActivateWindow(10147)")
        window = xbmcgui.Window(10147)
        xbmc.sleep(100)
        window.getControl(1).setLabel(translate(32000))
        window.getControl(5).setText(translate(32065))
        while xbmc.getCondVisibility("Window.IsActive(10147)"):
            xbmc.sleep(100)
        ret = xbmcgui.Dialog().yesno(translate(32000), translate(32067))
        if ret:
            xbmc.executebuiltin("RunAddon(script.keymap)")

    except:
        traceback.print_stack()
        xbmc.executebuiltin("XBMC.Notification('" + translate(32000) + "','" + translate(32066) + "','2000','')")

#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
from xbmcaddon import Addon
import utils


# Addon info
__addonID__ = "script.filecleaner"
__addon__ = Addon(__addonID__)
__title__ = __addon__.getAddonInfo("name")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo("profile")).decode("utf-8")


class LogViewerDialog(xbmcgui.WindowXMLDialog):
    """
    The LogViewerDialog class is an extension of the default windows supplied with XBMC.

    It is used to display the contents of a log file, and as such uses a fullscreen window to show as much text as
    possible. It also contains two buttons for trimming and clearing the contents of the log file.
    """
    CAPTIONID = 201
    TEXTBOXID = 202
    TRIMBUTTONID = 301
    CLEARBUTTONID = 302
    CLOSEBUTTONID = 303

    def __init__(self, xml_filename, script_path, default_skin="Default", default_res="720p", *args, **kwargs):
        self.log = utils.Log()
        self.caption = utils.translate(32603)
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(self.CAPTIONID).setLabel(self.caption)
        self.getControl(self.TEXTBOXID).setText(self.log.get())

    def onClick(self, control_id, *args):
        if control_id == self.TRIMBUTTONID:
            if xbmcgui.Dialog().yesno(utils.translate(32604), utils.translate(32605), utils.translate(32607)):
                self.getControl(self.TEXTBOXID).setText(self.log.trim())
        elif control_id == self.CLEARBUTTONID:
            if xbmcgui.Dialog().yesno(utils.translate(32604), utils.translate(32606), utils.translate(32607)):
                self.getControl(self.TEXTBOXID).setText(self.log.clear())
        elif control_id == self.CLOSEBUTTONID:
            self.close()
        else:
            utils.debug("Unknown button pressed", xbmc.LOGERROR)


if __name__ == "__main__":
    win = LogViewerDialog("DialogLogViewer.xml", __addon__.getAddonInfo("path"))
    win.doModal()
    del win

#!/usr/bin/python
# -*- coding: utf-8 -*-

import utils
from xbmcgui import Dialog, WindowXMLDialog


class LogViewerDialog(WindowXMLDialog):
    """
    The LogViewerDialog class is an extension of the default windows supplied with Kodi.

    It is used to display the contents of a log file, and as such uses a fullscreen window to show as much text as
    possible. It also contains two buttons for trimming and clearing the contents of the log file.
    """
    TEXTBOXID = 202
    TRIMBUTTONID = 301
    CLEARBUTTONID = 302

    def __init__(self, xml_filename, script_path, default_skin="Default", default_res="720p", *args, **kwargs):
        self.log = utils.Log()
        WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(self.TEXTBOXID).setText(self.log.get())

    def onClick(self, control_id, *args):
        if control_id == self.TRIMBUTTONID:
            if Dialog().yesno(utils.translate(32604), utils.translate(32605), utils.translate(32607)):
                self.getControl(self.TEXTBOXID).setText(self.log.trim())
        elif control_id == self.CLEARBUTTONID:
            if Dialog().yesno(utils.translate(32604), utils.translate(32606), utils.translate(32607)):
                self.getControl(self.TEXTBOXID).setText(self.log.clear())
        else:
            raise ValueError("Unknown button pressed")


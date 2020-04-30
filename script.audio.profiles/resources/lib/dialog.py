# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

from kodi_six import xbmc, xbmcgui
from resources.lib import notify
from resources.lib.addoninfo import *

KODIMONITOR = xbmc.Monitor()
KODIPLAYER = xbmc.Player()


class DIALOG:

    def start(self, xml_file, labels=None, textboxes=None, buttons=None, thelist=0, force_dialog=False):
        count = 0
        if ADDON.getSetting('player_show').lower() == 'true':
            delay = int(ADDON.getSetting('player_autoclose_delay'))
            autoclose = ADDON.getSetting('player_autoclose').lower()
        else:
            delay = 10
            autoclose = 'false'
        display = SHOW(xml_file, ADDON_PATH, labels=labels, textboxes=textboxes, buttons=buttons, thelist=thelist)
        display.show()
        while (KODIPLAYER.isPlaying() or force_dialog) and not KODIMONITOR.abortRequested():
            if force_dialog:
                notify.logDebug('the current returned value from display is: %s' % str(display.ret))
                if display.ret is not None:
                    break
            elif autoclose == 'true':
                if count >= delay:
                    break
                count = count + 1
            KODIMONITOR.waitForAbort( 1 )
        ret = display.ret
        del display
        return ret



class SHOW(xbmcgui.WindowXMLDialog):

    def __init__(self, xmlFile, resourcePath, labels, textboxes, buttons, thelist):
        self.ret = None
        if labels:
            self.labels = labels
        else:
            self.labels = {}
        if textboxes:
            self.textboxes = textboxes
        else:
            self.textboxes = {}
        if buttons:
            self.buttons = buttons
        else:
            self.buttons = []
        self.thelist = thelist


    def onInit(self):
        # set labels
        for label, label_text in list(self.labels.items()):
            self.getControl(label).setLabel(label_text)
        # set textboxes
        for textbox, textbox_text in list(self.textboxes.items()):
            self.getControl(textbox).setText(textbox_text)
        # set buttons
        self.listitem = self.getControl(self.thelist)
        for button_text in self.buttons:
            self.listitem.addItem(xbmcgui.ListItem(button_text))
        # focus on list
        self.setFocus(self.listitem)
        # set amount of buttons for background height
        xbmcgui.Window(10000).setProperty(ADDON_ID + '_items', str(len(self.buttons)))


    def onClick(self, controlID):
        # return selected button
        self.ret = self.getControl(controlID).getSelectedPosition()
        self.close()

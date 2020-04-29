# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

from kodi_six import xbmc, xbmcaddon, xbmcgui
import resources.lib.notify as notify

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))
KODIMONITOR = xbmc.Monitor()
KODIPLAYER = xbmc.Player()


class DIALOG:

    def start(self, xml_file, labels=None, textboxes=None, buttons=None, thelist=0, save_profile=False):
        count = 0
        delay = int(ADDON.getSetting('player_autoclose_delay'))
        autoclose = ADDON.getSetting('player_autoclose').lower()
        display = SHOW(xml_file, ADDON_PATH, labels=labels, textboxes=textboxes, buttons=buttons, thelist=thelist)
        display.show()
        while (KODIPLAYER.isPlaying() or save_profile) and not KODIMONITOR.abortRequested():
            if save_profile:
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

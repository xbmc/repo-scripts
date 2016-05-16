# -*- coding: utf-8 -*-

import xbmcaddon
import xbmcgui
import xbmc
import os

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonpath__           = xbmc.translatePath(__addon__.getAddonInfo('path'))
__lang__                = __addon__.getLocalizedString
__path_img__            = os.path.join(__addonpath__, 'resources', 'media' )

ACTION_PREVIOUS_MENU        = 10
ACTION_STEP_BACK            = 21
ACTION_NAV_BACK             = 92
ACTION_MOUSE_RIGHT_CLICK    = 101
ACTION_BACKSPACE            = 110
KEY_BUTTON_BACK             = 275
BACK_GROUP = [ACTION_PREVIOUS_MENU, ACTION_STEP_BACK, ACTION_NAV_BACK, ACTION_MOUSE_RIGHT_CLICK, ACTION_BACKSPACE, KEY_BUTTON_BACK]

ACTION_MOVE_LEFT            = 1
ACTION_MOVE_RIGHT           = 2
ACTION_MOVE_UP              = 3
ACTION_MOVE_DOWN            = 4

REMOTE_0                    = 58
REMOTE_1                    = 59
REMOTE_2                    = 60
REMOTE_3                    = 61
REMOTE_4                    = 62
REMOTE_5                    = 63
REMOTE_6                    = 64
REMOTE_7                    = 65
REMOTE_8                    = 66
REMOTE_9                    = 67
NUMBERS_GROUP = [REMOTE_0, REMOTE_1, REMOTE_2, REMOTE_3, REMOTE_4, REMOTE_5, REMOTE_6, REMOTE_7, REMOTE_8, REMOTE_9]

buttons = {
    11020: 0,
    11021: 1,
    11022: 2,
    11023: 3,
    11024: 4,
    11025: 5,
    11026: 6,
    11027: 7,
    11028: 8,
    11029: 9,
    11030: 10
}

class DIALOG:
    def start(self, item, profile):
        
        display = SHOW("script-user-rating-rateDialog.xml", __addonpath__, item=item, profile=profile)
        display.doModal()
        rating = display.rating
        del display
        return rating
        
class SHOW(xbmcgui.WindowXMLDialog):
    
    def __init__(self, xmlFile, resourcePath, item, profile):
        # set window property to true
        xbmcgui.Window(10000).setProperty(__addon_id__ + '_running', 'True')
        
        self.rating = None
        self.item = item
        self.profile = profile
        
    def onInit(self):
        self.getControl(10010).setLabel('[B]' + self.profile + '[/B]')
        self.getControl(10012).setLabel(self.item['title'])
        self.setFocus(self.getControl(buttons.keys()[self.item['rating']]))
    
    def onClick(self, controlID):
        self.rating = buttons[controlID]
        self.close()
        
    def onAction(self, action):
        if action in BACK_GROUP:
            self.close()
            
        if action in NUMBERS_GROUP:
            digit = NUMBERS_GROUP.index(action)
            self.setFocus(self.getControl(buttons.keys()[digit]))
            
    
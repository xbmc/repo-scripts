# -*- coding: utf-8 -*-

import json
import xbmcgui
import xbmc
import sys
import os
import xbmcaddon

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__icon__                = __addon__.getAddonInfo('icon')
__addonpath__           = xbmc.translatePath(__addon__.getAddonInfo('path'))
__lang__                = __addon__.getLocalizedString
__path__                = os.path.join(__addonpath__, 'resources', 'lib' )
__path_img__            = os.path.join(__addonpath__, 'resources', 'media' )

sys.path.append(__path__)


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

import debug

class GUI():
    def __init__(self):
        
        self.main()
        
    def main(self):
        
        # declarate media type
        d_for = ['movie', 'tvshow', 'episode']
        
        #get settings.xml
        self.onWatched      = __addon__.getSetting('onWatched')
        self.onlyNotRated   = __addon__.getSetting('onlyNotRated')
        
        item = {}
        
        # open settings dialog if no parameter
        if (len(sys.argv) == 0 or len(sys.argv[0]) == 0):
            __addon__.openSettings()
        
        # detect that user or service run script
        if len(sys.argv) > 3:
            self.runFromService = True;
            try:
                item = self.getData(sys.argv[2], sys.argv[3])
            except:
                return
        else:
            self.runFromService = False;
            item['mType'] = xbmc.getInfoLabel('ListItem.DBTYPE')
            item['dbID'] = xbmc.getInfoLabel('ListItem.DBID')
            item['rating'] = 0 if xbmc.getInfoLabel('ListItem.UserRating') == "" else int(xbmc.getInfoLabel('ListItem.UserRating'))
            item['title'] = xbmc.getInfoLabel('ListItem.Title')
        
        debug.debug('Retrive data: rating:' + str(item['rating']) + ' media:' + item['mType'] + ' ID:' + item['dbID'] + ' title:' + item['title'])
        
        if item['mType'] not in d_for:
            return;
        
        # check conditions from settings
        if self.runFromService is True:
            if 'false' in self.onWatched:
                return
            if 'true' in self.onlyNotRated and item['rating'] > 0:
                return
            
        # display window rating
        display = WindowRating(item)
        display.doModal()
        del display
        
    def getData(self, dbID, mType):
        jsonGetSource = '{"jsonrpc": "2.0", "method": "VideoLibrary.Get' + mType.title() + 'Details", "params": { "properties" : ["title", "userrating"], "' + mType + 'id": ' + str(dbID) + '}, "id": "1"}'
        jsonGetSource = xbmc.executeJSONRPC(jsonGetSource)
        jsonGeResponse = json.loads(unicode(jsonGetSource, 'utf-8', errors='ignore'))
        
        debug.debug(str(jsonGeResponse))
        
        if 'result' in jsonGeResponse and mType + 'details' in jsonGeResponse['result']:
            title = jsonGeResponse['result'][mType + 'details']['title'].encode('utf-8')
            rating = jsonGeResponse['result'][mType + 'details']['userrating']
        else:
            title = ""
            rating = 0
            
        return { 'dbID': dbID, 'mType': mType, 'title': title, 'rating': rating }
        
class WindowRating(xbmcgui.WindowDialog):
    
    def __init__(self, item):
        
        # set window property to true
        xbmcgui.Window(10000).setProperty(__addon_id__ + '_running', 'True')
        
        # set vars
        self.item = item
        
        self.button = []
        
        # create window
        bgResW = 520
        bgResH = 160
        bgPosX = (1280 - bgResW) / 2
        bgPosY = (720 - bgResH) / 2
        self.bg = xbmcgui.ControlImage(bgPosX, bgPosY, bgResW, bgResH, __path_img__+'//bg.png')
        self.addControl(self.bg)
        self.labelTitle = xbmcgui.ControlLabel(bgPosX+20, bgPosY+20, bgResW-40, bgResH-40, '[B]' + __lang__(32100) + ':[/B]', 'font14', '0xFF0084ff',  alignment=2)
        self.addControl(self.labelTitle)
        self.label = xbmcgui.ControlLabel(bgPosX+20, bgPosY+54, bgResW-40, bgResH-40, item['title'], 'font13', '0xFFFFFFFF',  alignment=2)
        self.addControl(self.label)
        
        # create button list
        self.starLeft = bgPosX+40
        self.starTop = bgPosY+96
        for i in range(11):
            if i == 0:
                self.button.append(xbmcgui.ControlButton(self.starLeft, self.starTop, 30, 30, "", focusTexture=__path_img__ + '//star0f.png', noFocusTexture=__path_img__ + '//star0.png'))
            else:
                if i <= self.item['rating']:
                    self.button.append(xbmcgui.ControlButton(self.starLeft+(i*40), self.starTop, 30, 30, "", focusTexture=__path_img__ + '//star2f.png', noFocusTexture=__path_img__ + '//star2.png'))
                else:
                    self.button.append(xbmcgui.ControlButton(self.starLeft+(i*40), self.starTop, 30, 30, "", focusTexture=__path_img__ + '//star2f.png', noFocusTexture=__path_img__ + '//star1.png'))
                
            self.addControl(self.button[i])
        self.setFocus(self.button[self.item['rating']])
        
    def onAction(self, action):
        if action in BACK_GROUP:
            self.close()
            
        if action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_UP:
            if self.item['rating'] < 10:
                self.item['rating'] = self.item['rating'] + 1
            self.setFocus(self.button[self.item['rating']])
            
        if action == ACTION_MOVE_LEFT or action == ACTION_MOVE_DOWN:
            if self.item['rating'] > 0:
                self.item['rating'] = self.item['rating'] - 1
            self.setFocus(self.button[self.item['rating']])
            
        if action in NUMBERS_GROUP:
            self.item['rating'] = NUMBERS_GROUP.index(action)
            self.setFocus(self.button[self.item['rating']])
        
    def onControl(self, control):
        for i in range(11):
            if control == self.button[i]:
                self.addVote(self.item, str(i))
                self.close()
                
    def addVote(self, item, rateing):
        jsonAdd = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.Set' + item['mType'].title() + 'Details", "params": {"' + item['mType'] + 'id" : ' + item['dbID'] + ', "userrating": ' + rateing + '}}'
        xbmc.executeJSONRPC(jsonAdd)

# lock script to prevent duplicates
if (xbmcgui.Window(10000).getProperty(__addon_id__ + '_running') != 'True'):
    GUI()
    xbmcgui.Window(10000).clearProperty(__addon_id__ + '_running')

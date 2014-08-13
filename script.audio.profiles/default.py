# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os

__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')
__addonpath__ = xbmc.translatePath(__addon__.getAddonInfo('path'))
__datapath__ = xbmc.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/') + '/'
__path_img__ = __addonpath__ + '/images/'
__lang__ = __addon__.getLocalizedString

ACTION_PREVIOUS_MENU = 10
ACTION_SELECT_ITEM = 7
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_STEP_BACK = 21
ACTION_NAV_BACK = 92
ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_MOUSE_MOVE = 107
ACTION_BACKSPACE = 110
KEY_BUTTON_BACK = 275

class Start:

    def __init__(self):
        # detect mode, check args
        try:
            mode = str(sys.argv[1])
        except:
            mode = False

        # start GUI or switch audio
        if mode == False:
            gui = GUI()
            gui.doModal()
            del gui
        elif mode == '0' or mode == '1' or mode == '2' or mode == '3' or mode == '4':
            switch = Switch()
            switch.check(mode)
        else:
            xbmc.log('## AUDIO PROFILES ##: Wrong arg, use like RunScript("' + __addon_id__ + ',x") x - number of profile')

# GUI to configure audio profiles
class GUI(xbmcgui.WindowDialog):

    def __init__(self):
        # set vars
        self.sName = {}
        self.sProfile = {}
        self.sProfile[1]      = __addon__.getSetting('profile1')
        self.sName[1]         = __addon__.getSetting('name1')
        self.sProfile[2]      = __addon__.getSetting('profile2')
        self.sName[2]         = __addon__.getSetting('name2')
        self.sProfile[3]      = __addon__.getSetting('profile3')
        self.sName[3]         = __addon__.getSetting('name3')
        self.sProfile[4]      = __addon__.getSetting('profile4')
        self.sName[4]         = __addon__.getSetting('name4')
        
        # set background
        self.button = {}
        bgResW = 520
        bgResH = 340
        bgPosX = (1280 - bgResW) / 2
        bgPosY = (720 - bgResH) / 2
        self.start = 1
        
        # add controls
        self.bg = xbmcgui.ControlImage(bgPosX, bgPosY, bgResW, bgResH, __path_img__ + 'bg.png')
        self.addControl(self.bg)
        
        self.strActionInfo = xbmcgui.ControlLabel(bgPosX, bgPosY+20, 520, 200, '', 'font14', '0xFFFFFFFF', alignment=2)
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel(__lang__(32100))
        
        self.button[1] = xbmcgui.ControlButton(bgPosX+30, bgPosY+80, 460, 50, self.sName[1], alignment=6, font='font13')
        self.addControl(self.button[1])
        self.setFocus(self.button[1])
        
        self.button[2] = xbmcgui.ControlButton(bgPosX+30, bgPosY+140, 460, 50, self.sName[2], alignment=6, font='font13')
        self.addControl(self.button[2])
        
        self.button[3] = xbmcgui.ControlButton(bgPosX+30, bgPosY+200, 460, 50, self.sName[3], alignment=6, font='font13')
        self.addControl(self.button[3])
        
        self.button[4] = xbmcgui.ControlButton(bgPosX+30, bgPosY+260, 460, 50, self.sName[4], alignment=6, font='font13')
        self.addControl(self.button[4])

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_STEP_BACK or action == ACTION_BACKSPACE or action == ACTION_NAV_BACK or action == KEY_BUTTON_BACK or action == ACTION_MOUSE_RIGHT_CLICK:
            self.close()
        if action == ACTION_MOVE_UP:
            if self.start > 1:
                self.start = self.start - 1
            self.setFocus(self.button[self.start])
        if action == ACTION_MOVE_DOWN:
            if self.start < 4:
                self.start = self.start + 1
            self.setFocus(self.button[self.start])
    
    def onControl(self, control):
        for key in self.button:
            if control == self.button[key]:
                self.save(key)
                self.close()
                    
    # get audio config and save to file
    def save(self, button):
    
        # get all settings from System / Audio section
        jsonGetSysSettings = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audiooutput"}},"id":1}')
        jsonGetSysSettings = unicode(jsonGetSysSettings, 'utf-8')
        jsonGetSysSettings = json.loads(jsonGetSysSettings)
        
        # get volume level
        jsonGetSysSettings2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}')
        jsonGetSysSettings2 = unicode(jsonGetSysSettings2, 'utf-8')
        jsonGetSysSettings2 = json.loads(jsonGetSysSettings2)
        
        # prepare json string
        jsonToWrite = ''
        if 'result' in jsonGetSysSettings:
            for set in jsonGetSysSettings['result']['settings']:
                if str(set['value']) == 'True' or str(set['value']) == 'False': # lowercase bolean values
                    set['value'] = str(set['value']).lower()
                jsonToWrite = jsonToWrite + '"' + str(set['id']) + '": "' + str(set['value']) + '", '
        jsonToWrite = '{' + jsonToWrite + '"volume": "' + str(jsonGetSysSettings2['result']['volume']) + '"}'
        
        # create dir in addon data if not exist
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)
        
        # save profile file
        f = xbmcvfs.File(__datapath__ + 'profile' + str(button) + '.json', 'w')
        result = f.write(jsonToWrite)
        f.close()
        
        Message().msg(__lang__(32102) + ' ' + str(button) + ' - ' + self.sName[button])

# switching profiles
class Switch:

    def check(self, mode):
        # set vars
        self.sName = {}
        self.sProfile = {}
        self.sProfile[1]      = __addon__.getSetting('profile1')
        self.sName[1]         = __addon__.getSetting('name1')
        self.sProfile[2]      = __addon__.getSetting('profile2')
        self.sName[2]         = __addon__.getSetting('name2')
        self.sProfile[3]      = __addon__.getSetting('profile3')
        self.sName[3]         = __addon__.getSetting('name3')
        self.sProfile[4]      = __addon__.getSetting('profile4')
        self.sName[4]         = __addon__.getSetting('name4')
        
        # check profile config
        self.aProfile = []
        
        # stop if all profile are disabled
        if 'true' not in self.sProfile.values():
            Message().msg(__lang__(32101))
            return False
        
        # stop if selected (mode) profile are disabled
        if mode != '0' and 'false' in self.sProfile[int(mode)]:
            Message().msg(__lang__(32101) + ': ' + self.sName[int(mode)])
            return False
                
        # check if profile have settings file
        for key in self.sProfile:
            if 'true' in self.sProfile[key]:
                if not xbmcvfs.exists(__datapath__ + 'profile' + str(key) + '.json'):
                    Message().msg(__lang__(32101) + ': ' + self.sName[key])
                    return False
                self.aProfile.append(str(key))
        
        # check mode
        if mode == '0':
            self.toggle(mode)
        else:
            self.profile(mode)
        
    def toggle(self, mode):
        # create profile file
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)
        # try read last active profile
        try:
            f = xbmcvfs.File(__datapath__ + 'profile')
            profile = f.read()
            f.close()
            if (len(self.aProfile) == 1) or (profile not in self.aProfile):
                profile = self.aProfile[0]
            else:
                ip = int(self.aProfile.index(profile))
                if len(self.aProfile) == ip:
                    profile == self.aProfile[0]
                else:
                    profile = self.aProfile[ip+1]
        except:
            profile = self.aProfile[0]
            
        self.profile(profile)
        
    def profile(self, profile):
        self.sVolume        = __addon__.getSetting('volume')
        
        # read settings from profile
        f = xbmcvfs.File(__datapath__ + 'profile'+profile+'.json', 'r')
        result = f.read()
        jsonResult = json.loads(result)
        f.close()
        
        # if volume level is enabled set it from readed profile file
        if 'true' in self.sVolume:
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": ' + jsonResult['volume'] + '}, "id": 1}')
        del jsonResult['volume']
        
        # set settings readed from profile file
        for req in jsonResult:
            if req == 'audiooutput.audiodevice' or req == 'audiooutput.passthroughdevice':
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "' + req + '", "value": "' + jsonResult[req] + '"}, "id": 1}')
            else:
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "' + req + '", "value": ' + jsonResult[req].lower() + '}, "id": 1}')
        
        Message().msg(self.sName[int(profile)])
        
        # write curent profile
        f = xbmcvfs.File(__datapath__ + 'profile', 'w')
        f.write(profile)
        f.close()

class Message:
    def msg(self, msg):
        xbmc.executebuiltin('Notification(Audio Profile,'+msg+', 4000, ' + __addonpath__ + '/icon.png)')
        
Start()
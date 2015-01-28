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

# set vars
sName = {}
sProfile = {}
sProfile[1]      = __addon__.getSetting('profile1')
sName[1]         = __addon__.getSetting('name1')
sProfile[2]      = __addon__.getSetting('profile2')
sName[2]         = __addon__.getSetting('name2')
sProfile[3]      = __addon__.getSetting('profile3')
sName[3]         = __addon__.getSetting('name3')
sProfile[4]      = __addon__.getSetting('profile4')
sName[4]         = __addon__.getSetting('name4')
        
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

        # check is profiles is set
        if 'true' not in sProfile.values():
            Message().msg(__lang__(32105).encode('utf-8'))
            xbmcaddon.Addon(id=__addon_id__).openSettings()
            
        else:
            # start GUI or switch audio
            if mode == False or mode == 'm':
                gui = GUI(mode)
                gui.doModal()
                del gui
            elif mode == '0' or mode == '1' or mode == '2' or mode == '3' or mode == '4':
                switch = Switch()
                switch.check(mode)
            else:
                xbmc.log('## AUDIO PROFILES ##: Wrong arg, use like RunScript("' + __addon_id__ + ',x") x - number of profile')

# start GUI
class GUI(xbmcgui.WindowDialog):

    def __init__(self, mode):
        
        self.mode = mode
        
        # check how many controls is enabled
        p_int = 0
        for p in sProfile:
            if 'true' in sProfile[p]:
                p_int += 1
                
        # button dimensions
        b_ResW = 460
        b_ResH = 50
        m_x = 30
        m_r = 0
        
        # set background
        self.button = {}
        bgResW = 520
        bgResH = 80 + p_int*60
        bgPosX = (1280 - bgResW) / 2
        bgPosY = (720 - bgResH) / 2
        self.start = 1
            
        # add controls
        self.bg = xbmcgui.ControlImage(bgPosX, bgPosY, bgResW, bgResH, __path_img__ + 'bg.png')
        self.addControl(self.bg)
            
        self.strActionInfo = xbmcgui.ControlLabel(bgPosX+30, bgPosY+10, b_ResW, b_ResH, '', 'font14', '0xFFFFFFFF', alignment=6)
        self.addControl(self.strActionInfo)
        
        if self.mode == 'm':
            self.strActionInfo.setLabel(__lang__(32106).encode('utf-8'))
        else:
            self.strActionInfo.setLabel(__lang__(32100).encode('utf-8'))
        
        self.b_enabled = []
        for i in range(1, 5):
            if 'true' in sProfile[i]:
                m_r += 1
                self.b_enabled.append(i)
                self.button[i] = xbmcgui.ControlButton(bgPosX+m_x, bgPosY+10+(m_r*60), b_ResW, b_ResH, sName[i], alignment=6, font='font13')
                self.addControl(self.button[i])
                
        self.setFocus(self.button[self.b_enabled[0]])
        
        # for actions
        self.start = 0
        self.end = len(self.b_enabled)
        
    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_STEP_BACK or action == ACTION_BACKSPACE or action == ACTION_NAV_BACK or action == KEY_BUTTON_BACK or action == ACTION_MOUSE_RIGHT_CLICK:
            xbmcgui.Window(10000).clearProperty('audio_profiles_menu')
            self.close()
        if action == ACTION_MOVE_UP:
            if self.start > 0:
                self.start = self.start - 1
            self.setFocus(self.button[self.b_enabled[self.start]])
        if action == ACTION_MOVE_DOWN:
            if self.start < self.end-1:
                self.start = self.start + 1
            self.setFocus(self.button[self.b_enabled[self.start]])
        
    def onControl(self, control):
        for key in self.button:
            if control == self.button[key]:
                if self.mode == 'm':
                    Switch().profile(str(key))
                    xbmcgui.Window(10000).clearProperty('audio_profiles_menu')
                else:
                    self.save(key)
                self.close()
                    
    # get audio config and save to file
    def save(self, button):
        
        sVolume        = __addon__.getSetting('volume')
        sPlayer        = __addon__.getSetting('player')
        sVideo         = __addon__.getSetting('video')
        
        settingsToSave = {}
        
        # get all settings from System / Audio section
        json_s = ['{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audiooutput"}},"id":1}']
        
        # get volume level
        if 'true' in sVolume:
            json_s.append('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}')
        
        # get all settings from Video / Playback section
        if 'true' in sPlayer:
            json_s.append('{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"videos","category":"videoplayer"}}, "id":1}')
        
        # get all settings from System / Video section
        if 'true' in sVideo:
            json_s.append('{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"videoscreen"}}, "id":1}')
        
        # send json requests
        for j in json_s:
            jsonGetSysSettings = xbmc.executeJSONRPC(j)
            jsonGetSysSettings = unicode(jsonGetSysSettings, 'utf-8')
            jsonGetSysSettings = json.loads(jsonGetSysSettings)
            
            if 'result' in jsonGetSysSettings:
                if 'settings' in jsonGetSysSettings['result']:
                    for set in jsonGetSysSettings['result']['settings']:
                        if 'value' in set.keys():
                            settingsToSave[set['id']] = set['value']
                if 'volume' in jsonGetSysSettings['result']:
                    settingsToSave['volume'] = jsonGetSysSettings['result']['volume']
                
        # change all value to string
        if len(settingsToSave) > 0:
            for set, val in settingsToSave.items():
                if str(val) == 'True' or str(val) == 'False': # lowercase bolean values
                    settingsToSave[set] = str(val).lower()
                else:
                    settingsToSave[set] = str(val)
        
        # prepare JSON string to save to file
        jsonToWrite = str(json.dumps(settingsToSave))
        
        # create dir in addon data if not exist
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)
        
        # save profile file
        f = xbmcvfs.File(__datapath__ + 'profile' + str(button) + '.json', 'w')
        result = f.write(jsonToWrite)
        f.close()
        
        Message().msg(__lang__(32102).encode('utf-8') + ' ' + str(button) + ' (' + sName[button] + ')')

# switching profiles
class Switch:

    def check(self, mode):
        
        # check profile config
        self.aProfile = []
                
        # stop if selected (mode) profile are disabled
        if mode != '0' and 'false' in sProfile[int(mode)]:
            Message().msg(__lang__(32103).encode('utf-8') + ' (' + sName[int(mode)] + ')')
            return False
                
        # check if profile have settings file
        for key in sProfile:
            if 'true' in sProfile[key]:
                if not xbmcvfs.exists(__datapath__ + 'profile' + str(key) + '.json'):
                    Message().msg(__lang__(32101).encode('utf-8') + ' ' + str(key) + ' (' + sName[key] + ')')
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
        
        # read settings from profile
        f = xbmcvfs.File(__datapath__ + 'profile'+profile+'.json', 'r')
        result = f.read()
        try:
            jsonResult = json.loads(result)
            f.close()
        except:
            Message().msg(__lang__(32104).encode('utf-8') + ' ' + profile + ' (' + sName[int(profile)] + ')')
            return False
        
        # settings needed quote for value
        quote_needed = [
        'audiooutput.audiodevice',
        'audiooutput.passthroughdevice',
        'locale.audiolanguage'
        ]
        # set settings readed from profile file
        for setName, setValue in jsonResult.items():
            # add quotes
            if setName in quote_needed:
                setValue = '"' + setValue + '"'
            # set setting
            if setName == 'volume':
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": ' + jsonResult['volume'] + '}, "id": 1}')
            else:
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "' + setName + '", "value": ' + setValue + '}, "id": 1}')
        
        Message().msg(sName[int(profile)])
        
        # write curent profile
        f = xbmcvfs.File(__datapath__ + 'profile', 'w')
        f.write(profile)
        f.close()

class Message:
    def msg(self, msg):
        xbmc.executebuiltin('Notification(Audio Profile,'+msg+', 4000, ' + __addonpath__ + '/icon.png)')
        
Start()
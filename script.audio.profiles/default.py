# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
import sys

ADDON               = xbmcaddon.Addon()
ADDON_ID            = ADDON.getAddonInfo('id')
ADDON_NAME          = ADDON.getAddonInfo('name')
ADDON_ICON          = ADDON.getAddonInfo('icon')
ADDON_PATH          = xbmc.translatePath(ADDON.getAddonInfo('path'))
ADDON_PATH_DATA     = xbmc.translatePath(os.path.join('special://profile/addon_data/', ADDON_ID)).replace('\\', '/') + '/'
ADDON_PATH_LIB      = os.path.join(ADDON_PATH, 'resources', 'lib' )
ADDON_PATH_MEDIA    = os.path.join(ADDON_PATH, 'resources', 'media' )
ADDON_LANG          = ADDON.getLocalizedString

sys.path.append(ADDON_PATH_LIB)

import dialog
import debug

# set vars
sName = {
    1: ADDON.getSetting('name1'),
    2: ADDON.getSetting('name2'),
    3: ADDON.getSetting('name3'),
    4: ADDON.getSetting('name4')
}
sProfile = {
    1: ADDON.getSetting('profile1'),
    2: ADDON.getSetting('profile2'),
    3: ADDON.getSetting('profile3'),
    4: ADDON.getSetting('profile4')
}

class PROFILES:

    def __init__(self):
        debug.debug('[SYS.ARGV]: ' + str(sys.argv))
        
        # detect mode, check args
        if (len(sys.argv) < 2 or len(sys.argv[0]) == 0):
            mode = False
        else:
            mode = str(sys.argv[1])
        debug.debug('[MODE]: ' + str(mode))
        self.start(mode)
        
    def start(self, mode):
        xbmcgui.Window(10000).clearProperty(ADDON_ID + '_autoclose')
        
        # check is profiles is set
        if 'true' not in sProfile.values():
            debug.notify(ADDON_LANG(32105))
            xbmcaddon.Addon(id=ADDON_ID).openSettings()
        
        if mode is False:
            self.save()
            return
        
        if mode == 'service':
            enabledProfiles = self.getEnabledProfiles()
            xbmcgui.Window(10000).setProperty(ADDON_ID + '_autoclose', '1' if 'true' in ADDON.getSetting('player_autoclose') else '0')
            ret = dialog.DIALOG().start('script-audio-profiles-menu.xml', labels={10071: ADDON_LANG(32106)}, buttons=enabledProfiles[1], list=10070)
            if ret is not None:
                self.profile(str(enabledProfiles[0][ret]))
            return
            
        if mode == '0' or mode == '1' or mode == '2' or mode == '3' or mode == '4':
            if self.check(mode) is False:
                return
            
            if mode == '0':
                self.toggle(mode)
            else:
                self.profile(mode)
            return
            
        debug.debug('Wrong arg, use like RunScript("' + ADDON_ID + ',x") x - number of profile')

    def getEnabledProfiles(self):
        enabledProfileKey = []
        enabledProfileName = []
        for k, p in sProfile.items():
            if 'true' in p:
                enabledProfileKey.append(k)
                enabledProfileName.append(sName[k])
        return [enabledProfileKey, enabledProfileName]
    
    # get audio config and save to file
    def save(self):
        xbmc_version = int(xbmc.getInfoLabel('System.BuildVersion')[0:2])
        debug.debug('[XBMC VERSION]: ' + str(xbmc_version))
        
        enabledProfiles = self.getEnabledProfiles()
        ret = dialog.DIALOG().start('script-audio-profiles-menu.xml', labels={10071: ADDON_LANG(32100)}, buttons=enabledProfiles[1], list=10070)
        if ret is None:
            return False
        else:
            button = enabledProfiles[0][ret]
        
        settingsToSave = {}
        
        if xbmc_version < 17:
            json_s = [
            # get all settings from System / Audio section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audiooutput"}},"id":1}',
            # get volume level
            '{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}',
            # get all settings from Video / Playback section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"videos","category":"videoplayer"}}, "id":1}',
            # get all settings from System / Video section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"videoscreen"}}, "id":1}'
            ]
        else:
            json_s = [
            # get all settings from System / Audio section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audio"}},"id":1}',
            # get volume level
            '{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}',
            # get all settings from Video / Playback section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"player","category":"videoplayer"}}, "id":1}',
            # get all settings from System / Video section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"display"}}, "id":1}'
            ]
            
        # send json requests
        for j in json_s:
            jsonGet = xbmc.executeJSONRPC(j)
            jsonGet = json.loads(unicode(jsonGet, 'utf-8'))
            debug.debug('[JSON]: ' + str(jsonGet))
            
            if 'result' in jsonGet:
                if 'settings' in jsonGet['result']:
                    for set in jsonGet['result']['settings']:
                        if 'value' in set.keys():
                        
                            if set['value'] == True or set['value'] == False: # lowercase bolean values
                                settingsToSave[set['id']] = str(set['value']).lower()
                            else:
                                if type(set['value']) is int:
                                    settingsToSave[set['id']] = str(set['value'])
                                else:
                                    settingsToSave[set['id']] = str(set['value']).encode('utf-8')
                
                if 'volume' in jsonGet['result']:
                    settingsToSave['volume'] = str(jsonGet['result']['volume'])
        
        # prepare JSON string to save to file
        jsonToWrite = json.dumps(settingsToSave)
        
        # create dir in addon data if not exist
        if not xbmcvfs.exists(ADDON_PATH_DATA):
            xbmcvfs.mkdir(ADDON_PATH_DATA)
        
        # save profile file
        f = xbmcvfs.File(ADDON_PATH_DATA + 'profile' + str(button) + '.json', 'w')
        result = f.write(jsonToWrite)
        f.close()
        
        debug.notify(ADDON_LANG(32102) + ' ' + str(button) + ' (' + sName[button] + ')')

    def check(self, mode):
        # check profile config
        self.aProfile = []
        
        # stop if selected (mode) profile are disabled
        if mode != '0' and 'false' in sProfile[int(mode)]:
            debug.notify(ADDON_LANG(32103) + ' (' + sName[int(mode)] + ')')
            debug.debug('[CHECK]: This profile is dosabled in addon settings - ' + str(mode))
            return False
        
        # check if profile have settings file
        for key in sProfile:
            if 'true' in sProfile[key]:
                if not xbmcvfs.exists(ADDON_PATH_DATA + 'profile' + str(key) + '.json'):
                    debug.notify(ADDON_LANG(32101) + ' ' + str(key) + ' (' + sName[key] + ')')
                    debug.debug('[PROFILE FILE]: not exist for profile - ' + str(key))
                    return False
                self.aProfile.append(str(key))
        
    def toggle(self, mode):
        # create profile file
        if not xbmcvfs.exists(ADDON_PATH_DATA):
            xbmcvfs.mkdir(ADDON_PATH_DATA)
        # try read last active profile
        try:
            f = xbmcvfs.File(ADDON_PATH_DATA + 'profile')
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
        # read addon settings
        sVolume        = ADDON.getSetting('volume')
        sPlayer        = ADDON.getSetting('player')
        sVideo         = ADDON.getSetting('video')
        
        # read settings from profile
        f = xbmcvfs.File(ADDON_PATH_DATA + 'profile' + profile + '.json', 'r')
        result = f.read()
        try:
            jsonResult = json.loads(result)
            f.close()
        except:
            debug.notify(ADDON_LANG(32104) + ' ' + profile + ' (' + sName[int(profile)] + ')')
            debug.debug('[LOAD JSON FROM FILE]: Error reading from profile - ' + str(profile))
            return False
        
        # settings needed quote for value
        quote_needed = [
        'audiooutput.audiodevice',
        'audiooutput.passthroughdevice',
        'locale.audiolanguage'
        ]
        
        # set settings readed from profile file
        for setName, setValue in jsonResult.items():
            # skip setting that type is disable to changing
            if 'false' in sPlayer and setName.startswith('videoplayer'):
                continue
            if 'false' in sVideo and setName.startswith('videoscreen'):
                continue
            
            debug.debug('[RESTORING SETTING]: ' + setName + ': ' + setValue)
            # add quotes
            if setName in quote_needed:
                setValue = '"' + setValue + '"'
            # set setting
            if 'true' in sVolume and setName == 'volume':
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": ' + jsonResult['volume'] + '}, "id": 1}')
            else:
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "' + setName + '", "value": ' + setValue.encode('utf-8') + '}, "id": 1}')
        
        debug.notify(sName[int(profile)].decode('utf-8'))
        
        # write curent profile
        f = xbmcvfs.File(ADDON_PATH_DATA + 'profile', 'w')
        f.write(profile)
        f.close()

PROFILES()
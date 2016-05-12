# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
import sys

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__icon__                = __addon__.getAddonInfo('icon')
__addonpath__           = xbmc.translatePath(__addon__.getAddonInfo('path'))
__datapath__            = xbmc.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/') + '/'
__lang__                = __addon__.getLocalizedString
__path__                = os.path.join(__addonpath__, 'resources', 'lib' )
__path_img__            = os.path.join(__addonpath__, 'resources', 'media' )

sys.path.append(__path__)

import dialog
import debug

# set vars
sName = {
    1: __addon__.getSetting('name1'),
    2: __addon__.getSetting('name2'),
    3: __addon__.getSetting('name3'),
    4: __addon__.getSetting('name4')
}
sProfile = {
    1: __addon__.getSetting('profile1'),
    2: __addon__.getSetting('profile2'),
    3: __addon__.getSetting('profile3'),
    4: __addon__.getSetting('profile4')
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
        xbmcgui.Window(10000).clearProperty(__addon_id__ + '_autoclose')
        
        # check is profiles is set
        if 'true' not in sProfile.values():
            debug.notify(__lang__(32105))
            xbmcaddon.Addon(id=__addon_id__).openSettings()
        
        if mode is False:
            self.save()
            return
        
        if mode == 'service':
            enabledProfiles = self.getEnabledProfiles()
            xbmcgui.Window(10000).setProperty(__addon_id__ + '_autoclose', '1' if 'true' in __addon__.getSetting('player_autoclose') else '0')
            ret = dialog.DIALOG().start('script-audio-profiles-menu.xml', labels={10071: __lang__(32106)}, buttons=enabledProfiles[1], list=10070)
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
            
        debug.debug('Wrong arg, use like RunScript("' + __addon_id__ + ',x") x - number of profile')

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
        ret = dialog.DIALOG().start('script-audio-profiles-menu.xml', labels={10071: __lang__(32100)}, buttons=enabledProfiles[1], list=10070)
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
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)
        
        # save profile file
        f = xbmcvfs.File(__datapath__ + 'profile' + str(button) + '.json', 'w')
        result = f.write(jsonToWrite)
        f.close()
        
        debug.notify(__lang__(32102) + ' ' + str(button) + ' (' + sName[button] + ')')

    def check(self, mode):
        # check profile config
        self.aProfile = []
        
        # stop if selected (mode) profile are disabled
        if mode != '0' and 'false' in sProfile[int(mode)]:
            debug.notify(__lang__(32103) + ' (' + sName[int(mode)] + ')')
            debug.debug('[CHECK]: This profile is dosabled in addon settings - ' + str(mode))
            return False
        
        # check if profile have settings file
        for key in sProfile:
            if 'true' in sProfile[key]:
                if not xbmcvfs.exists(__datapath__ + 'profile' + str(key) + '.json'):
                    debug.notify(__lang__(32101) + ' ' + str(key) + ' (' + sName[key] + ')')
                    debug.debug('[PROFILE FILE]: not exist for profile - ' + str(key))
                    return False
                self.aProfile.append(str(key))
        
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
        # read addon settings
        sVolume        = __addon__.getSetting('volume')
        sPlayer        = __addon__.getSetting('player')
        sVideo         = __addon__.getSetting('video')
        
        # read settings from profile
        f = xbmcvfs.File(__datapath__ + 'profile' + profile + '.json', 'r')
        result = f.read()
        try:
            jsonResult = json.loads(result)
            f.close()
        except:
            debug.notify(__lang__(32104) + ' ' + profile + ' (' + sName[int(profile)] + ')')
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
        
        debug.notify(sName[int(profile)])
        
        # write curent profile
        f = xbmcvfs.File(__datapath__ + 'profile', 'w')
        f.write(profile)
        f.close()

PROFILES()
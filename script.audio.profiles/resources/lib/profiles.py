# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

from kodi_six import xbmc, xbmcaddon, xbmcvfs
import json, os, sys
import resources.lib.dialog as dialog
import resources.lib.notify as notify

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))
ADDON_PATH_DATA = xbmc.translatePath( ADDON.getAddonInfo('profile') )
ADDON_LANG = ADDON.getLocalizedString

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
cecCommands = ['', 'CECActivateSource', 'CECStandby', 'CECToggleState']
xbmc_version = int(xbmc.getInfoLabel('System.BuildVersion')[0:2])

def convert(data):
    if isinstance(data, bytes):      return data.decode()
    if isinstance(data, (str, int)): return str(data)
    if isinstance(data, dict):       return dict(map(convert, data.items()))
    if isinstance(data, tuple):      return tuple(map(convert, data))
    if isinstance(data, list):       return list(map(convert, data))
    if isinstance(data, set):        return set(map(convert, data))



class PROFILES:

    def __init__(self):
        notify.logInfo('running profiles script')
        notify.logDebug('[SYS.ARGV]: %s' % str(sys.argv))
        notify.logDebug('[XBMC VERSION]: %s' % str(xbmc_version))
        self.xmlFile = 'script-audio-profiles-menu.xml'
        # detect mode, check args
        if (len(sys.argv) < 2 or len(sys.argv[0]) == 0):
            mode = False
        else:
            mode = str(sys.argv[1])
        notify.logDebug('[MODE]: %s' % str(mode))
        self.start(mode)


    def start(self, mode):
        # check is profiles is set
        if 'true' not in sProfile.values():
            notify.popup(ADDON_LANG(32105))
            xbmcaddon.Addon(id=ADDON_ID).openSettings()
        if mode is False:
            self.save()
            return
        if mode == 'popup':
            enabledProfiles = self.getEnabledProfiles()
            ret = dialog.DIALOG().start(self.xmlFile, labels={10071: ADDON_LANG(32106)}, buttons=enabledProfiles[1],
                                        thelist=10070)
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
        notify.logError('Wrong arg, use like RunScript("%s,x") x - number of profile' % ADDON_ID)


    def getEnabledProfiles(self):
        enabledProfileKey = []
        enabledProfileName = []
        for k, p in sProfile.items():
            if 'true' in p:
                enabledProfileKey.append(k)
                enabledProfileName.append(sName[k])
        return [enabledProfileKey, enabledProfileName]


    def save(self):
        # get audio config and save to file
        enabledProfiles = self.getEnabledProfiles()
        ret = dialog.DIALOG().start(self.xmlFile, labels={10071: ADDON_LANG(32100)}, buttons=enabledProfiles[1],
                                    thelist=10070, save_profile=True)
        notify.logDebug( 'the returned value is %s' % str(ret) )
        if ret is None:
            return False
        else:
            button = enabledProfiles[0][ret]
        settingsToSave = {}
        json_s = [
            # get all settings from System / Audio section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audio"}},"id":1}',
            # get volume level
            '{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}',
            # get all settings from Player / Videos section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"player","category":"videoplayer"}}, "id":1}',
            # get all settings from System / Video section
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"display"}}, "id":1}'
                 ]
        # send json requests
        for j in json_s:
            jsonGet = xbmc.executeJSONRPC(j)
            jsonGet = json.loads(jsonGet)
            notify.logDebug('[JSON]: %s' % str(jsonGet))
            if 'result' in jsonGet:
                if 'settings' in jsonGet['result']:
                    for theset in jsonGet['result']['settings']:
                        if 'value' in theset.keys():

                            if theset['value'] == True or theset['value'] == False:  # lowercase bolean values
                                settingsToSave[theset['id']] = str(theset['value']).lower()
                            else:
                                if isinstance(theset['value'],int):
                                    settingsToSave[theset['id']] = str(theset['value'])
                                else:
                                    settingsToSave[theset['id']] = str(theset['value']).encode('utf-8')

                if 'volume' in jsonGet['result']:
                    settingsToSave['volume'] = str(jsonGet['result']['volume'])
        # prepare JSON string to save to file
        if xbmc_version > 18:
            settingsToSave = convert(settingsToSave)
        jsonToWrite = json.dumps(settingsToSave)
        # create dir in addon data if not exist
        if not xbmcvfs.exists(ADDON_PATH_DATA):
            xbmcvfs.mkdir(ADDON_PATH_DATA)
        # save profile file
        notify.logInfo('[SAVING SETTING]: %s' % sName[button])
        f = xbmcvfs.File(os.path.join(ADDON_PATH_DATA, 'profile%s.json' % str(button)), 'w')
        f.write(jsonToWrite)
        f.close()
        notify.popup('%s %s (%s)' % (ADDON_LANG(32102), str(button), sName[button]), force=True)


    def check(self, mode):
        # check profile config
        self.aProfile = []
        # stop if selected (mode) profile are disabled
        if mode != '0' and 'false' in sProfile[int(mode)]:
            notify.popup('%s (%s)' % (ADDON_LANG(32103), sName[int(mode)]))
            notify.logInfo('[CHECK]: This profile is disabled in addon settings - %s' % str(mode))
            return False
        # check if profile have settings file
        for key in sProfile:
            if 'true' in sProfile[key]:
                if not xbmcvfs.exists(ADDON_PATH_DATA + 'profile' + str(key) + '.json'):
                    notify.popup('%s %s (%s)' % (ADDON_LANG(32101), str(key), sName[key]))
                    notify.logError('[PROFILE FILE]: not exist for profile - %s' % str(key))
                    return False
                self.aProfile.append(str(key))


    def toggle(self, mode):
        # create profile file
        if not xbmcvfs.exists(ADDON_PATH_DATA):
            xbmcvfs.mkdir(ADDON_PATH_DATA)
        # try read last active profile
        f = xbmcvfs.File(os.path.join(ADDON_PATH_DATA,'profile'))
        try:
            profile = f.read()
        except IOError:
            profile = ''
        f.close()
        if profile:
            if (len(self.aProfile) == 1) or (profile not in self.aProfile):
                profile = self.aProfile[0]
            else:
                ip = int(self.aProfile.index(profile))
                if len(self.aProfile) == ip:
                    try:
                        profile = self.aProfile[0]
                    except IndexError:
                        profile = self.aProfile[0]
                else:
                    try:
                        profile = self.aProfile[ip + 1]
                    except IndexError:
                        profile = self.aProfile[0]
        else:
            profile = self.aProfile[0]
        self.profile(profile)


    def profile(self, profile):
        # read addon settings
        sVolume = ADDON.getSetting('volume')
        sPlayer = ADDON.getSetting('player')
        sVideo = ADDON.getSetting('video')
        sCec = ADDON.getSetting('profile' + profile + '_cec')
        # read settings from profile
        f = xbmcvfs.File(os.path.join(ADDON_PATH_DATA, 'profile' + profile + '.json'), 'r')
        result = f.read()
        try:
            jsonResult = json.loads(result)
            f.close()
        except ValueError:
            notify.popup('%s %s (%s)' % (ADDON_LANG(32104), profile, sName[int(profile)]))
            notify.logError('[LOAD JSON FROM FILE]: Error reading from profile - %s' % str(profile))
            return False
        # settings needed quote for value
        quote_needed = ['audiooutput.audiodevice',
                        'audiooutput.passthroughdevice',
                        'locale.audiolanguage',
                        'lookandfeel.soundskin']
        # set settings readed from profile file
        notify.logInfo('[RESTORING SETTING]: %s' % sName[int(profile)])
        for setName, setValue in jsonResult.items():
            # skip setting that type is disable to changing
            if 'false' in sPlayer and setName.startswith('videoplayer'):
                continue
            if 'false' in sVideo and setName.startswith('videoscreen'):
                continue
            notify.logDebug('[RESTORING SETTING]: %s: %s' % (setName,setValue))
            # add quotes
            if setName in quote_needed:
                setValue = '"%s"' % setValue
            # set setting
            if 'true' in sVolume and setName == 'volume':
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": %s}, "id": 1}' % jsonResult['volume'])
            else:
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "%s", "value": %s}, "id": 1}' % (setName, setValue))
        notify.popup(sName[int(profile)])
        # write curent profile
        f = xbmcvfs.File(os.path.join(ADDON_PATH_DATA, 'profile'), 'w')
        f.write(profile)
        f.close()
        # CEC
        if sCec != '' and int(sCec) > 0:
            notify.logInfo('[SENDING CEC COMMAND]: %s' % cecCommands[int(sCec)])
            xbmc.executebuiltin(cecCommands[int(sCec)])

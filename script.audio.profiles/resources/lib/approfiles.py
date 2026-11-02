
import json
import os
import sys
import xbmc
import xbmcgui
from resources.lib import apdialog
from resources.lib.fileops import *


class Profiles:

    def __init__(self, settings, lw, auto=False):
        """Handles audio profile switching."""
        self.LW = lw
        self.SETTINGS = settings
        self.AUTO = auto
        self.SNAME = {1: self.SETTINGS['name1'],
                      2: self.SETTINGS['name2'],
                      3: self.SETTINGS['name3'],
                      4: self.SETTINGS['name4'],
                      5: self.SETTINGS['name5'],
                      6: self.SETTINGS['name6'],
                      7: self.SETTINGS['name7'],
                      8: self.SETTINGS['name8'],
                      9: self.SETTINGS['name9'],
                      10: self.SETTINGS['name10']}
        self.SPROFILE = {1: self.SETTINGS['profile1'],
                         2: self.SETTINGS['profile2'],
                         3: self.SETTINGS['profile3'],
                         4: self.SETTINGS['profile4'],
                         5: self.SETTINGS['profile5'],
                         6: self.SETTINGS['profile6'],
                         7: self.SETTINGS['profile7'],
                         8: self.SETTINGS['profile8'],
                         9: self.SETTINGS['profile9'],
                         10: self.SETTINGS['profile10']}
        self.APROFILE = []
        self.CECCOMMANDS = ['', 'CECActivateSource',
                            'CECStandby', 'CECToggleState']
        self.ENABLEDPROFILES = self._get_enabled_profiles()
        self.KODIPLAYER = xbmc.Player()
        self.DIALOG = xbmcgui.Dialog()
        self.NOTIFYTIME = self.SETTINGS['notify_time'] * 1000
        self.DISPLAYNOTIFICATION = self.SETTINGS['notify']
        success, loglines = checkPath(
            os.path.join(self.SETTINGS['ADDONDATAPATH'], ''))
        self.LW.log(loglines)

    def changeProfile(self, mode):
        if True not in self.SPROFILE.values():
            self._notification(self.SETTINGS['ADDONLANGUAGE'](
                32105), self.SETTINGS['notify_maintenance'])
            self.SETTINGS['ADDON'].openSettings()
        if mode is False:
            self._save()
            return
        if mode == 'popup':
            force_dialog = not self.KODIPLAYER.isPlaying()
            dialog_return, loglines = apdialog.Dialog().start(self.SETTINGS, title=self.SETTINGS['ADDONLANGUAGE'](32106),
                                                              buttons=self.ENABLEDPROFILES[1], force_dialog=force_dialog)
            self.LW.log(loglines)
            if dialog_return is not None:
                self._profile(str(self.ENABLEDPROFILES[0][dialog_return]))
            return dialog_return
        if int(mode) <= 10:
            if self._check(mode) is False:
                return
            if mode == '0':
                self._toggle(mode)
            else:
                self._profile(mode)
            return
        self.LW.log(['Wrong argument used - use like RunScript("%s,x") x (x is the number of the profile)' %
                    self.SETTINGS['ADDONNAME']], xbmc.LOGERROR)

    def _check(self, mode):
        if mode != '0' and not self.SPROFILE[int(mode)]:
            self._notification('%s (%s)' % (self.SETTINGS['ADDONLANGUAGE'](
                32103), self.SNAME[int(mode)]), self.SETTINGS['notify_maintenance'])
            self.LW.log(
                ['CHECK: This profile is disabled in addon settings - %s' % str(mode)], xbmc.LOGINFO)
            return False
        for key in self.SPROFILE:
            if self.SPROFILE[key]:
                success, loglines = checkPath(os.path.join(
                    self.SETTINGS['ADDONDATAPATH'], 'profile%s.json' % str(key)), createdir=False)
                self.LW.log(loglines)
                if not success:
                    self._notification('%s %s (%s)' % (self.SETTINGS['ADDONLANGUAGE'](32101), str(key), self.SNAME[key]),
                                       self.SETTINGS['notify_maintenance'])
                    self.LW.log(
                        ['PROFILE FILE does not exist for profile - %s' % str(key)], xbmc.LOGERROR)
                    return False
                self.APROFILE.append(str(key))

    def _convert(self, data):
        if sys.version_info < (3, 0):
            return data
        if isinstance(data, bytes):
            return data.decode()
        if isinstance(data, (str, int)):
            return str(data)
        if isinstance(data, dict):
            return dict(list(map(self._convert, list(data.items()))))
        if isinstance(data, tuple):
            return tuple(map(self._convert, data))
        if isinstance(data, list):
            return list(map(self._convert, data))
        if isinstance(data, set):
            return set(map(self._convert, data))

    def _get_enabled_profiles(self):
        enabled_profile_key = []
        enabled_profile_name = []
        for thekey, profile in self.SPROFILE.items():
            if profile:
                enabled_profile_key.append(thekey)
                enabled_profile_name.append(self.SNAME[thekey])
        return [enabled_profile_key, enabled_profile_name]

    def _notification(self, msg, display=True):
        if self.DISPLAYNOTIFICATION and display:
            self.DIALOG.notification(
                self.SETTINGS['ADDONLONGNAME'], msg, icon=self.SETTINGS['ADDONICON'], time=self.NOTIFYTIME)

    def _profile(self, profile):
        loglines, result = readFile(os.path.join(
            self.SETTINGS['ADDONDATAPATH'], 'profile%s.json' % profile))
        self.LW.log(loglines)
        try:
            jsonResult = json.loads(result)
        except ValueError:
            self._notification('%s %s (%s)' % (self.SETTINGS['ADDONLANGUAGE'](32104), profile, self.SNAME[int(profile)]),
                               self.SETTINGS['notify_maintenance'])
            self.LW.log(['LOAD JSON FROM FILE: Error reading from profile - %s' %
                        str(profile)], xbmc.LOGERROR)
            return False
        quote_needed = ['audiooutput.audiodevice',
                        'audiooutput.passthroughdevice',
                        'locale.audiolanguage',
                        'lookandfeel.soundskin']
        self.LW.log(['RESTORING SETTING: %s' %
                    self.SNAME[int(profile)]], xbmc.LOGINFO)
        for set_name, set_value in jsonResult.items():
            if not self.SETTINGS['player'] and set_name.startswith('videoplayer'):
                continue
            if not self.SETTINGS['video'] and set_name.startswith('videoscreen'):
                continue
            self.LW.log(['RESTORING SETTING: %s: %s' % (set_name, set_value)])
            if set_name in quote_needed:
                set_value = '"%s"' % set_value
            if self.SETTINGS['volume'] and set_name == 'volume':
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": %s}, "id": 1}' % jsonResult['volume'])
            else:
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Settings.SetSettingValue", "params": {"setting": "%s", "value": %s}, "id": 1}' % (set_name, set_value))
        if self.AUTO:
            show_notification = self.SETTINGS['notify_auto']
        else:
            show_notification = self.SETTINGS['notify_manual']
        self._notification(self.SNAME[int(profile)], show_notification)
        success, loglines = writeFile(profile, os.path.join(
            self.SETTINGS['ADDONDATAPATH'], 'profile'), 'w')
        self.LW.log(loglines)
        s_cec = self.SETTINGS['profile%s_cec' % profile]
        if s_cec:
            self.LW.log(['SENDING CEC COMMAND: %s' %
                        self.CECCOMMANDS[s_cec]], xbmc.LOGINFO)
            xbmc.executebuiltin(self.CECCOMMANDS[s_cec])

    def _save(self):
        dialog_return, loglines = apdialog.Dialog().start(self.SETTINGS, title=self.SETTINGS['ADDONLANGUAGE'](32106),
                                                          buttons=self.ENABLEDPROFILES[1], force_dialog=True)
        self.LW.log(loglines)
        self.LW.log(['the returned value is %s' % str(dialog_return)])
        if dialog_return is None:
            return False
        else:
            button = self.ENABLEDPROFILES[0][dialog_return]
        settings_to_save = {}
        json_s = [
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"audio"}},"id":1}',
            '{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume"]}, "id": 1}',
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"player","category":"videoplayer"}}, "id":1}',
            '{"jsonrpc":"2.0","method":"Settings.GetSettings", "params":{"level": "expert", "filter":{"section":"system","category":"display"}}, "id":1}'
        ]
        for j in json_s:
            json_get = xbmc.executeJSONRPC(j)
            json_get = json.loads(json_get)
            self.LW.log(['JSON: %s' % str(json_get)])
            if 'result' in json_get:
                if 'settings' in json_get['result']:
                    for theset in json_get['result']['settings']:
                        if 'value' in theset.keys():
                            if theset['value'] == True or theset['value'] == False:
                                settings_to_save[theset['id']] = str(
                                    theset['value']).lower()
                            else:
                                if isinstance(theset['value'], int):
                                    settings_to_save[theset['id']] = str(
                                        theset['value'])
                                else:
                                    settings_to_save[theset['id']] = str(
                                        theset['value']).encode('utf-8')

                if 'volume' in json_get['result']:
                    settings_to_save['volume'] = str(
                        json_get['result']['volume'])
        json_to_write = json.dumps(self._convert(settings_to_save))
        self.LW.log(['SAVING SETTING: %s' % self.SNAME[button]], xbmc.LOGINFO)
        success, loglines = writeFile(json_to_write, os.path.join(
            self.SETTINGS['ADDONDATAPATH'], 'profile%s.json' % str(button)), 'w')
        self.LW.log(loglines)
        if success:
            self._notification('%s %s (%s)' % (self.SETTINGS['ADDONLANGUAGE'](32102), str(button),
                                               self.SNAME[button]), self.SETTINGS['notify_maintenance'])

    def _toggle(self, mode):
        loglines, profile = readFile(os.path.join(
            self.SETTINGS['ADDONDATAPATH'], 'profile'))
        self.LW.log(loglines)
        if profile:
            if (len(self.APROFILE) == 1) or (profile not in self.APROFILE):
                profile = self.APROFILE[0]
            else:
                ip = int(self.APROFILE.index(profile))
                if len(self.APROFILE) == ip:
                    try:
                        profile = self.APROFILE[0]
                    except IndexError:
                        profile = self.APROFILE[0]
                else:
                    try:
                        profile = self.APROFILE[ip + 1]
                    except IndexError:
                        profile = self.APROFILE[0]
        else:
            profile = self.APROFILE[0]
        self._profile(profile)

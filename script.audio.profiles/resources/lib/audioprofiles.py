# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

import xbmc
import json
import os
import sys
from resources.lib.fileops import *
from resources.lib.xlogger import Logger
from resources.lib.apsettings import loadSettings
from resources.lib.approfiles import Profiles


def _upgrade():
    settings = loadSettings()
    if settings['version_upgrade'] != settings['ADDONVERSION']:
        settings['ADDON'].setSetting(
            'version_upgrade', settings['ADDONVERSION'])


class apManual:

    def __init__(self):
        """Runs the audio profiler switcher manually."""
        settings = loadSettings()
        lw = Logger(preamble='[Audio Profiles]', logdebug=settings['debug'])
        lw.log(['script version %s started' %
               settings['ADDONVERSION']], xbmc.LOGINFO)
        lw.log(['debug logging set to %s' % settings['debug']], xbmc.LOGINFO)
        lw.log(['SYS.ARGV: %s' % str(sys.argv)])
        lw.log(['loaded settings', settings])
        profiles = Profiles(settings, lw)
        try:
            mode = sys.argv[1]
        except IndexError:
            mode = False
        lw.log(['MODE: %s' % str(mode)])
        profiles.changeProfile(mode)
        lw.log(['script version %s stopped' %
               settings['ADDONVERSION']], xbmc.LOGINFO)


class apMonitor(xbmc.Monitor):

    def __init__(self):
        """Starts the background process for automatic audio profile switching."""
        xbmc.Monitor.__init__(self)
        _upgrade()
        self._init_vars()
        self.LW.log(['background monitor version %s started' %
                    self.SETTINGS['ADDONVERSION']], xbmc.LOGINFO)
        self.LW.log(['debug logging set to %s' %
                    self.SETTINGS['debug']], xbmc.LOGINFO)
        self._change_profile(
            self.SETTINGS['auto_default'], forceload=self.SETTINGS['force_auto_default'])
        while not self.abortRequested():
            if self.waitForAbort(10):
                break
        self.LW.log(['background monitor version %s stopped' %
                    self.SETTINGS['ADDONVERSION']], xbmc.LOGINFO)

    def onNotification(self, sender, method, data):
        data = json.loads(data)
        if 'System.OnWake' in method:
            self.LW.log(['MONITOR METHOD: %s DATA: %s' %
                        (str(method), str(data))])
            self._change_profile(self.SETTINGS['auto_default'])
        if 'Player.OnStop' in method:
            self.LW.log(['MONITOR METHOD: %s DATA: %s' %
                        (str(method), str(data))])
            self.waitForAbort(1)
            if not self.KODIPLAYER.isPlaying():
                self._change_profile(self.SETTINGS['auto_gui'])
        if 'Player.OnPlay' in method:
            self.LW.log(['MONITOR METHOD: %s DATA: %s' %
                        (str(method), str(data))])
            self._auto_switch(data)

    def onSettingsChanged(self):
        self._init_vars()

    def _init_vars(self):
        self.SETTINGS = loadSettings()
        self.PROFILESLIST = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        # this only includes mappings we are 100% sure are accurate every time
        self.MAPTYPE = {'video': 'auto_videos', 'episode': 'auto_tvshows',
                        'musicvideo': 'auto_musicvideo', 'song': 'auto_music'}
        self.LW = Logger(
            preamble='[Audio Profiles Service]', logdebug=self.SETTINGS['debug'])
        self.PROFILES = Profiles(self.SETTINGS, self.LW, auto=True)
        self.KODIPLAYER = xbmc.Player()
        self.LW.log(['the settings are:', self.SETTINGS])
        self.LW.log(['initialized variables'])

    def _auto_switch(self, data):
        if self.SETTINGS['player_show']:
            self.LW.log(['showing select menu'])
            if self.PROFILES.changeProfile('popup') is not None:
                self.LW.log(['option selected, returning'])
                return
            self.LW.log(
                ['select menu timed out or was closed with no selection - continuing to auto select'])
        content_autoswitch = self._auto_switch_content(data)
        self.LW.log(['got a content autoswitch of %s' % content_autoswitch])
        if content_autoswitch not in ['auto_music', 'auto_pvr_radio']:
            codec_setting, channels_setting = self._auto_switch_stream()
            if codec_setting != '0':
                the_setting = codec_setting
                self.LW.log(['using the codec setting of %s' % the_setting])
            elif channels_setting != '0':
                the_setting = channels_setting
                self.LW.log(['using the channels setting of %s' % the_setting])
            elif self.SETTINGS['aggressive_music_match'] and codec_setting == '0' and channels_setting == '0' and content_autoswitch == 'auto_unknown':
                the_setting = self.SETTINGS['auto_music']
                self.LW.log(
                    ['stream does not seem to be video, using the auto_music setting of %s' % the_setting])
            else:
                the_setting = self.SETTINGS[content_autoswitch]
                self.LW.log(['using the content setting of %s' % the_setting])
        else:
            the_setting = self.SETTINGS[content_autoswitch]
            self.LW.log(['using the content setting of %s' % the_setting])
        self._change_profile(the_setting)

    def _auto_switch_stream(self):
        if self.SETTINGS['codec_delay'] > 0:
            self.LW.log(['waiting %s seconds before trying to get stream details' % str(
                self.SETTINGS['codec_delay'])])
            self.waitForAbort(self.SETTINGS['codec_delay'])
        response = xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":1, "properties":["currentaudiostream"]}, "id":1}')
        r_dict = json.loads(response)
        self.LW.log(['got back audio stream data of:', r_dict])
        try:
            codec = r_dict['result']['currentaudiostream']['codec']
        except (IndexError, KeyError, ValueError, TypeError):
            codec = None
        try:
            channels = r_dict['result']['currentaudiostream']['channels']
        except (IndexError, KeyError, ValueError, TypeError):
            channels = None
        self.LW.log(['got %s for the codec and %s for the channels' %
                    (str(codec), str(channels))])
        if codec:
            codec_set = 'auto_othercodec'
            for check_codec in ['ac3', 'eac3', 'dts', 'dtshd', 'truehd']:
                if codec in check_codec:
                    codec_set = 'auto_%s' % check_codec
                    break
        else:
            codec_set = 'none'
        try:
            codec_setting = self.SETTINGS[codec_set]
        except KeyError:
            codec_setting = '0'
        if channels:
            if channels > 2:
                channels_set = 'auto_multichannel'
            else:
                channels_set = 'auto_stereo'
        else:
            channels_set = 'none'
        try:
            channels_setting = self.SETTINGS[channels_set]
        except KeyError:
            channels_setting = '0'
        self.LW.log(['got codec set of %s and channels set of %s' %
                    (codec_set, channels_set)])
        self.LW.log(['sending back codec setting of %s and channel setting of %s' % (
            codec_setting, channels_setting)])
        return codec_setting, channels_setting

    def _auto_switch_content(self, data):
        try:
            thetype = data['item']['type']
        except KeyError:
            self.LW.log(
                ['data did not include valid item and/or type for playing media - aborting'])
            return
        self.LW.log(['the type is: %s' % thetype])
        theset = self.MAPTYPE.get(thetype)
        if not theset:
            if thetype == 'movie':
                # if video is a PVR recording assign to auto_pvr_tv
                if self._check_playing_file('pvr://'):
                    theset = 'auto_pvr_tv'
                # if video is not from library assign to auto_videos
                elif 'id' not in data['item']:
                    theset = 'auto_videos'
                # it must actually be a movie
                else:
                    theset = 'auto_movies'
            # distinguish pvr TV and pvr RADIO
            elif 'channel' in thetype and 'channeltype' in data['item']:
                if 'tv' in data['item']['channeltype']:
                    theset = 'auto_pvr_tv'
                elif 'radio' in data['item']['channeltype']:
                    theset = 'auto_pvr_radio'
                else:
                    theset = 'auto_unknown'
            # detect cdda that kodi return as unknown
            elif thetype == 'unknown':
                if self._check_playing_file('cdda://'):
                    theset = 'auto_music'
                else:
                    theset = 'auto_unknown'
            else:
                theset = 'auto_unknown'
            self.LW.log(['got %s from the content auto switch' % theset])
        return theset

    def _change_profile(self, profile, forceload=False):
        if profile in self.PROFILESLIST:
            last_profile = self._get_last_profile()
            self.LW.log(
                ['Last loaded profile: %s To switch profile: %s' % (last_profile, profile)])
            if last_profile != profile or forceload:
                self.PROFILES.changeProfile(profile)
            else:
                self.LW.log(['Same profile - profiles not switched'])
        elif profile == str(len(self.PROFILESLIST) + 1):
            self.LW.log(
                ['this auto switch setting is set to show the select menu - showing menu'])
            self.PROFILES.changeProfile('popup')

    def _check_playing_file(self, thestr):
        try:
            thefile = self.KODIPLAYER.getPlayingFile()
        except RuntimeError:
            self.LW.log(['error trying to get playing file from Kodi'])
            return False
        self.LW.log(['the playing file is: %s' % thefile])
        return thefile.startswith(thestr)

    def _get_last_profile(self):
        loglines, profile = readFile(os.path.join(
            self.SETTINGS['ADDONDATAPATH'], 'profile'))
        self.LW.log(loglines)
        if profile in self.PROFILESLIST:
            return profile
        else:
            return ''

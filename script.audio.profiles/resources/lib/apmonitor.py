# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original Audio Profiles code by Regss
# *  updates and additions through v1.4.1 by notoco and CtrlGy
# *  updates and additions since v1.4.2 by pkscout

from kodi_six import xbmc, xbmcvfs
import json, os
from resources.lib import notify
from resources.lib.addoninfo import *

profiles = ['1', '2', '3', '4']
map_type = {'movie': 'auto_movies', 'video': 'auto_videos', 'episode': 'auto_tvshows', 'channel': 'auto_pvr',
            'musicvideo': 'auto_musicvideo', 'song': 'auto_music', 'unknown': 'auto_unknown'}
susppend_auto_change = False
set_for_susspend = None



class Monitor(xbmc.Monitor):
    def __init__(self):
        notify.logInfo('staring background monitor process')
        xbmc.Monitor.__init__(self)
        # default for kodi start
        self.changeProfile(ADDON.getSetting('auto_default'), forceload=ADDON.getSetting('force_auto_default'))


    def onSettingsChanged(self):
        global ADDON
        reload (ADDON)

    def onNotification(self, sender, method, data):
        global susppend_auto_change
        global set_for_susspend
        data = json.loads(data)
        if 'System.OnWake' in method:
            notify.logDebug('[MONITOR] METHOD: %s DATA: %s' % (str(method), str(data)))
            # default for kodi wakeup
            self.changeProfile(ADDON.getSetting('auto_default'))
        if 'Player.OnStop' in method:
            notify.logDebug('[MONITOR] METHOD: %s DATA: %s' % (str(method), str(data)))
            # gui
            susppend_auto_change = False
            self.changeProfile(ADDON.getSetting('auto_gui'))
        if 'Player.OnPlay' in method:
            notify.logDebug('[MONITOR] METHOD: %s DATA: %s' % (str(method), str(data)))
            # auto switch
            if 'item' in data and 'type' in data['item']:
                self.autoSwitch(data)


    def autoSwitch(self, data):
        global susppend_auto_change
        global set_for_susspend
        thetype = data['item']['type']
        theset = map_type.get(thetype)
        # auto show dialog
        notify.logDebug('the data are:')
        notify.logDebug(data)
        if 'true' in ADDON.getSetting('player_show'):
            xbmc.executebuiltin('RunScript(%s, popup)' % ADDON_ID)
        # if video is not from library assign to auto_videos
        if 'movie' in thetype and 'id' not in data['item']:
            theset = 'auto_videos'
        # distinguish pvr TV and pvr RADIO
        if 'channel' in thetype and 'channeltype' in data['item']:
            if 'tv' in data['item']['channeltype']:
                theset = 'auto_pvr_tv'
            elif 'radio' in data['item']['channeltype']:
                theset = 'auto_pvr_radio'
            else:
                theset = None
        # detect cdda that kodi return as unknown
        if 'unknown' in thetype and 'player' in data and 'playerid' in data['player']:
            jsonS = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "id": "1", "method": "Player.GetItem", "params": {"playerid": %s, "properties": ["file"]}}' % str(data['player']['playerid'])
                                       )
            jsonR = json.loads(jsonS)
            try:
                thefile = jsonR['result']['item']['file']
            except (IndexError, KeyError, ValueError):
                thefile = ''
            if thefile.startswith('cdda://'):
                theset = 'auto_music'
        notify.logDebug('[MONITOR] Setting parsed: %s' % str(theset))
        # cancel susspend auto change when media thetype change
        if theset != set_for_susspend:
            susppend_auto_change = False
            set_for_susspend = theset
        if theset is not None:
            self.changeProfile(ADDON.getSetting(theset))
            susppend_auto_change = True


    def changeProfile(self, profile, forceload=''):
        if profile in profiles:
            # get last loaded profile
            lastProfile = self.getLastProfile()
            notify.logDebug('[MONITOR] Last loaded profile: %s To switch profile: %s' % (lastProfile, profile))
            if (lastProfile != profile and susppend_auto_change is not True) or forceload.lower() == 'true':
                xbmc.executebuiltin('RunScript(%s, %s)' % (ADDON_ID, profile))
            else:
                notify.logDebug('[MONITOR] Switching omitted (same profile) or switching is susspend')


    def getLastProfile(self):
        try:
            f = xbmcvfs.File(os.path.join(ADDON_PATH_DATA, 'profile'))
            p = f.read()
            f.close()
        except IOError:
            return ''
        if p in profiles:
            return p
        else:
            return ''

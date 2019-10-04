#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcaddon
import xbmcgui
import json
import time
import datetime
import os
import sys

########################

PYTHON3 = True if sys.version_info.major == 3 else False

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA_PATH = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID))
ADDON_DATA_IMG_PATH = os.path.join(xbmc.translatePath("special://profile/addon_data/%s/img" % ADDON_ID))

NOTICE = xbmc.LOGNOTICE
WARNING = xbmc.LOGWARNING
DEBUG = xbmc.LOGDEBUG

DIALOG = xbmcgui.Dialog()

PLAYER = xbmc.Player()
VIDEOPLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
MUSICPLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

########################

def get_kodiversion():
    build = xbmc.getInfoLabel('System.BuildVersion')
    return int(build[:2])


def addon_setting(skin,setting,save=False):
    profile = xbmc.getInfoLabel('System.ProfileName')
    setting_id = skin + '_' + profile + '_' + setting
    skin_version = xbmcaddon.Addon(skin).getAddonInfo('version')

    if not save:
        if ADDON.getSetting(id=setting_id) == skin_version:
            return True
        return False
    else:
        ADDON.setSetting(id=setting_id, value=skin_version)


def log(txt,loglevel=NOTICE,force=False):
    if ((loglevel == NOTICE or loglevel == WARNING) and ADDON.getSettingBool('log')) or loglevel == DEBUG or force:

        if not PYTHON3 and isinstance(txt, str):
            txt = txt.decode('utf-8')

        message = u'[ %s ] %s' % (ADDON_ID,txt)

        if not PYTHON3:
            xbmc.log(msg=message.encode('utf-8'), level=loglevel)
        else:
            xbmc.log(msg=message, level=loglevel)


def remove_quotes(label):
    if not label:
        return ''

    if label.startswith("'") and label.endswith("'") and len(label) > 2:
        label = label[1:-1]
        if label.startswith('"') and label.endswith('"') and len(label) > 2:
            label = label[1:-1]
        elif label.startswith('&quot;') and label.endswith('&quot;'):
            label = label[6:-6]

    return label


def get_date(date_time):
    date_time_obj = datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
    date_obj = date_time_obj.date()

    return date_obj


def execute(cmd):
    log('Execute: %s' % cmd, DEBUG)
    xbmc.executebuiltin(cmd)


def visible(condition):
    return xbmc.getCondVisibility(condition)


def clear_playlists():
    log('Clearing existing playlists')
    VIDEOPLAYLIST.clear()
    MUSICPLAYLIST.clear()


def gotopath(path,target='videos'):
    execute('Dialog.Close(all,true)')
    execute('Container.Update(%s)' % path) if visible('Window.IsMedia') else execute('ActivateWindow(%s,%s,return)' % (target,path))


def winprop(key, value=None, clear=False, window_id=10000):
    window = xbmcgui.Window(window_id)

    if clear:
        window.clearProperty(key.replace('.json', '').replace('.bool', ''))

    elif value is not None:

        if key.endswith('.json'):
            key = key.replace('.json', '')
            value = json.dumps(value)

        elif key.endswith('.bool'):
            key = key.replace('.bool', '')
            value = 'true' if value else 'false'

        window.setProperty(key, value)

    else:
        result = window.getProperty(key.replace('.json', '').replace('.bool', ''))

        if result:
            if key.endswith('.json'):
                result = json.loads(result)
            elif key.endswith('.bool'):
                result = result in ('true', '1')

        return result


def get_channeldetails(channel_name):
    channel_details = {}

    channels = json_call('PVR.GetChannels',
                        properties=['channel', 'uniqueid', 'icon', 'thumbnail'],
                        params={'channelgroupid': 'alltv'},
                        )

    try:
        for channel in channels['result']['channels']:
            if channel['channel'].encode('utf-8') == channel_name:
                channel_details['channelid'] = channel['channelid']
                channel_details['channel'] = channel['channel']
                channel_details['icon'] = channel['icon']
                break
    except Exception:
        return

    return channel_details


def get_bool(value,string='true'):
    try:
        if value.lower() == string:
            return True
        raise Exception

    except Exception:
        return False


def encode_string(string):
    if not PYTHON3:
        string = string.encode('utf-8')
    return string


def json_call(method,properties=None,sort=None,query_filter=None,limit=None,params=None,item=None,options=None,limits=None,debug=False):
    json_string = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}

    if properties is not None:
        json_string['params']['properties'] = properties

    if limit is not None:
        json_string['params']['limits'] = {'start': 0, 'end': int(limit)}

    if sort is not None:
        json_string['params']['sort'] = sort

    if query_filter is not None:
        json_string['params']['filter'] = query_filter

    if options is not None:
        json_string['params']['options'] = options

    if limits is not None:
        json_string['params']['limits'] = limits

    if item is not None:
        json_string['params']['item'] = item

    if params is not None:
        json_string['params'].update(params)

    json_string = json.dumps(json_string)
    result = xbmc.executeJSONRPC(json_string)

    if debug:
        log('--> JSON CALL: ' + json_string)
        log('--> JSON RESULT: ' + result)

    if not PYTHON3:
        result = unicode(result, 'utf-8', errors='ignore')

    return json.loads(result)


def reload_widgets(instant=False,force=True):
    log('Force widgets to refresh')
    timestamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())

    if instant:
        winprop('EmbuaryWidgetUpdate', timestamp)
        return

    execute('AlarmClock(WidgetRefresh,SetProperty(EmbuaryWidgetUpdate,%s,home),00:05,silent)' % timestamp)

    if force:
        execute('AlarmClock(WidgetForceRefresh1,SetProperty(EmbuaryForceWidgetUpdate,1,home),00:10,silent)')
        execute('AlarmClock(WidgetForceRefresh2,ClearProperty(EmbuaryForceWidgetUpdate,home),00:11,silent)')
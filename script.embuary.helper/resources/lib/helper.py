#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcaddon
import xbmcgui
import json
import time

########################

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

NOTICE = xbmc.LOGNOTICE
WARNING = xbmc.LOGWARNING
DEBUG = xbmc.LOGDEBUG

PLAYER = xbmc.Player()
VIDEOPLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
MUSICPLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

########################

def get_kodiversion():

    build = xbmc.getInfoLabel('System.BuildVersion')
    return int(build[:2])


def log(txt,loglevel=NOTICE,force=False):

    if ((loglevel == NOTICE or loglevel == WARNING) and ADDON.getSettingBool('log')) or (loglevel == DEBUG and ADDON.getSettingBool('debuglog')) or force:

        ''' Python 2 requires to decode stuff at first
        '''
        try:
            if isinstance(txt, str):
                txt = txt.decode('utf-8')
        except AttributeError:
            pass

        message = u'[ %s ] %s' % (ADDON_ID,txt)

        try:
            xbmc.log(msg=message.encode('utf-8'), level=loglevel) # Python 2
        except TypeError:
            xbmc.log(msg=message, level=loglevel)


def remove_quotes(label):

    if not label:
        return ''

    if label.startswith("'") and label.endswith("'") and len(label) > 2:
        label = label[1:-1]
        if label.startswith('"') and label.endswith('"') and len(label) > 2:
            label = label[1:-1]

    return label


def execute(cmd):

    log('Execute: %s' % cmd)
    xbmc.executebuiltin(cmd, DEBUG)


def visible(condition):

	return xbmc.getCondVisibility(condition)


def grabfanart():

    fanarts = list()

    movie_query = json_call('VideoLibrary.GetMovies',
                        properties=['art'],
                        sort={'method': 'random'}, limit=20
                        )

    try:
        for art in movie_query['result']['movies']:
                movie_fanart = art['art'].get('fanart', '')
                fanarts.append(movie_fanart)
    except Exception:
        log('Backgrounds: No movie artworks found.')

    tvshow_query = json_call('VideoLibrary.GetTVShows',
                        properties=['art'],
                        sort={'method': 'random'}, limit=20
                        )

    try:
        for art in tvshow_query['result']['tvshows']:
                tvshow_fanart = art['art'].get('fanart', '')
                fanarts.append(tvshow_fanart)
    except Exception:
        log('Backgrounds: No TV show artworks found.')

    return fanarts


def winprop(key, value=None, clear=False, window_id=10000):

    window = xbmcgui.Window(window_id)

    if clear:

        log('Clear prop: %s' % key)
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
            if channel['channel'] == channel_name:
                channel_details['channelid'] = channel['channelid']
                channel_details['channel'] = channel['channel']
                channel_details['icon'] = channel['icon']
                break
    except Exception:
        return

    return channel_details


def json_call(method,properties=None,sort=None,query_filter=None,limit=None,params=None,item=None):

    json_string = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}

    if properties is not None:
        json_string['params']['properties'] = properties

    if limit is not None:
        json_string['params']['limits'] = {'start': 0, 'end': limit}

    if sort is not None:
        json_string['params']['sort'] = sort

    if query_filter is not None:
        json_string['params']['filter'] = query_filter

    if item is not None:
        json_string['params']['item'] = item

    if params is not None:
        json_string['params'].update(params)

    json_string = json.dumps(json_string)

    result = xbmc.executeJSONRPC(json_string)

    ''' Python 2 compatibility
    '''
    try:
        result = unicode(result, 'utf-8', errors='ignore')
    except NameError:
        pass

    result = json.loads(result)

    log('json-string: %s' % json_string, DEBUG)
    log('json-result: %s' % result, DEBUG)

    return result


def reload_widgets(delay=False):

    log('Force widgets to refresh')
    timestamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())

    if delay:
        execute('AlarmClock(WidgetRefresh,SetProperty(EmbuaryWidgetUpdate,%s,home),00:04,silent)' % timestamp)
    else:
        winprop('EmbuaryWidgetUpdate', timestamp)


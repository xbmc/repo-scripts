#!/usr/bin/python
# coding: utf-8

########################

from __future__ import division

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json
import random
import os
import locale

''' Python 2<->3 compatibility
'''
try:
    import urllib
except ImportError:
    import urllib.parse as urllib

from resources.lib.helper import *
from resources.lib.library import *
from resources.lib.json_map import *
from resources.lib.image import *

########################

def restartservice(params):
    execute('NotifyAll(%s, restart)' % ADDON_ID)


def calc(params):
    prop = remove_quotes(params.get('prop','CalcResult'))
    formula = remove_quotes(params.get('do'))
    result = eval(str(formula))
    winprop(prop, str(result))


def settimer(params):
    actions = remove_quotes(params.get('do'))
    time = params.get('time','50')
    delay = params.get('delay')
    busydialog = get_bool(params.get('busydialog','true'))

    if busydialog:
        execute('ActivateWindow(busydialognocancel)')

    xbmc.sleep(int(time))
    execute('Dialog.Close(all,true)')

    while visible('Window.IsVisible(busydialognocancel)'):
        xbmc.sleep(10)

    for action in actions.split('||'):
        execute(action)
        if delay:
            xbmc.sleep(int(delay))


def encode(params):
    string = remove_quotes(params.get('string'))
    prop = params.get('prop','EncodedString')
    winprop(prop,urllib.quote(string))


def decode(params):
    string = remove_quotes(params.get('string'))
    prop = params.get('prop','DecodedString')
    winprop(prop,urllib.unquote(string))


def createselect(params):
    selectionlist = []
    indexlist = []
    headertxt = remove_quotes(params.get('header', ''))

    for i in range(1, 30):

        label = xbmc.getInfoLabel('Window.Property(Dialog.%i.Label)' % (i))

        if label == '':
            break
        elif label != 'none' and label != '-':
            selectionlist.append(label)
            indexlist.append(i)

    if selectionlist:
        index = DIALOG.select(headertxt, selectionlist)

        if index > -1:
            value = xbmc.getInfoLabel('Window.Property(Dialog.%i.Builtin)' % (indexlist[index]))
            for builtin in value.split('||'):
                execute(builtin)
                xbmc.sleep(30)

    for i in range(1, 30):
        execute('ClearProperty(Dialog.%i.Builtin)' % i)
        execute('ClearProperty(Dialog.%i.Label)' % i)


def dialogok(params):
    headertxt = remove_quotes(params.get('header', ''))
    bodytxt = remove_quotes(params.get('message', ''))
    DIALOG.ok(heading=headertxt, line1=bodytxt)


def dialogyesno(params):
    headertxt = remove_quotes(params.get('header', ''))
    bodytxt = remove_quotes(params.get('message', ''))
    yesactions = params.get('yesaction', '').split('|')
    noactions = params.get('noaction', '').split('|')

    if DIALOG.yesno(heading=headertxt, line1=bodytxt):
        for action in yesactions:
            execute(action)
    else:
        for action in noactions:
            execute(action)


def textviewer(params):
    headertxt = remove_quotes(params.get('header', ''))
    bodytxt = remove_quotes(params.get('message', ''))
    DIALOG.textviewer(headertxt, bodytxt)


def togglekodisetting(params):
    settingname = params.get('setting', '')
    value = False if visible('system.getbool(%s)' % settingname) else True

    json_call('Settings.SetSettingValue',
                params={'setting': '%s' % settingname, 'value': value}
                )


def getkodisetting(params):
    setting = params.get('setting')
    strip = params.get('strip')

    json_query = json_call('Settings.GetSettingValue',
                params={'setting': '%s' % setting}
                )

    try:
        result = json_query['result']
        result = result.get('value')

        if strip == 'timeformat':
            strip = ['(12h)', ('(24h)')]
            for value in strip:
                if value in result:
                    result = result[:-6]

        result = str(result)
        if result.startswith('[') and result.endswith(']'):
           result = result[1:-1]

        winprop(setting,result)

    except Exception:
        winprop(setting, clear=True)


def setkodisetting(params):
    settingname = params.get('setting', '')
    value = params.get('value', '')

    try:
        value = int(value)
    except Exception:
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False

    json_call('Settings.SetSettingValue',
                params={'setting': '%s' % settingname, 'value': value}
                )


def toggleaddons(params):
    addonid = params.get('addonid').split('+')
    enable = get_bool(params.get('enable'))

    for addon in addonid:

        try:
            json_call('Addons.SetAddonEnabled',
                params={'addonid': '%s' % addon, 'enabled': enable}
                )
            log('%s - enable: %s' % (addon, enable))
        except Exception:
            pass


def playsfx(params):
    xbmc.playSFX(remove_quotes(params.get('path', '')))


def playitem(params):
    clear_playlists()

    dbtype = params.get('dbtype')
    dbid = params.get('dbid')

    if dbtype =='episode':
        itemtype = 'episodeid'
    elif dbtype =='song':
        itemtype = 'songid'
    else:
        itemtype = 'movieid'

    execute('Dialog.Close(all,true)')

    if dbid:
        json_call('Player.Open',
                    item={itemtype: int(dbid)}
                    )
    else:
        execute('PlayMedia("%s")' % remove_quotes(params.get('item')))


def playfolder(params):
    clear_playlists()

    dbid = int(params.get('dbid'))
    shuffled = get_bool(params.get('shuffle'))

    if shuffled:
        winprop('script.shuffle.bool', True)

    if params.get('type') == 'season':
        json_query = json_call('VideoLibrary.GetSeasonDetails',
                                properties=['title','season','tvshowid'],
                                params={'seasonid': dbid}
                                )
        try:
            result = json_query['result']['seasondetails']
        except Exception as error:
            log('Play folder error getting season details: %s' % error)
            return

        json_query = json_call('VideoLibrary.GetEpisodes',
                                properties=episode_properties,
                                query_filter={'operator': 'is', 'field': 'season', 'value': '%s' % result['season']},
                                params={'tvshowid': int(result['tvshowid'])}
                                )
    else:
        json_query = json_call('VideoLibrary.GetEpisodes',
                            properties=episode_properties,
                            params={'tvshowid': dbid}
                            )

    try:
        result = json_query['result']['episodes']
    except Exception as error:
        log('Play folder error getting episodes: %s' % error)
        return

    for episode in result:
        json_call('Playlist.Add',
                item={'episodeid': episode['episodeid']},
                params={'playlistid': 1}
                )

    execute('Dialog.Close(all)')

    json_call('Player.Open',
            item={'playlistid': 1, 'position': 0},
            options={'shuffled': shuffled}
            )


def playall(params):
    clear_playlists()

    container = params.get('id')
    method = params.get('method')

    playlistid = 0 if params.get('type') == 'music' else 1
    shuffled = get_bool(method,'shuffle')

    if shuffled:
        winprop('script.shuffle.bool', True)

    if method == 'fromhere':
        method = 'Container(%s).ListItemNoWrap' % container
    else:
        method = 'Container(%s).ListItemAbsolute' % container

    for i in range(int(xbmc.getInfoLabel('Container(%s).NumItems' % container))):

        if visible('String.IsEqual(%s(%s).DBType,movie)' % (method,i)):
            media_type = 'movie'
        elif visible('String.IsEqual(%s(%s).DBType,episode)' % (method,i)):
            media_type = 'episode'
        elif visible('String.IsEqual(%s(%s).DBType,song)' % (method,i)):
            media_type = 'song'
        else:
            media_type = None

        dbid = xbmc.getInfoLabel('%s(%s).DBID' % (method,i))
        url = xbmc.getInfoLabel('%s(%s).Filenameandpath' % (method,i))

        if media_type and dbid:
            json_call('Playlist.Add',
                        item={'%sid' % media_type: int(dbid)},
                        params={'playlistid': playlistid}
                        )
        elif url:
            json_call('Playlist.Add',
                        item={'file': url},
                        params={'playlistid': playlistid}
                        )

    json_call('Player.Open',
                item={'playlistid': playlistid, 'position': 0},
                options={'shuffled': shuffled}
                )


def playrandom(params):
    clear_playlists()

    container = params.get('id')

    i = random.randint(1,int(xbmc.getInfoLabel('Container(%s).NumItems' % container)))

    if visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,movie)' % (container,i)):
        media_type = 'movie'
    elif visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,episode)' % (container,i)):
        media_type = 'episode'
    elif visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,song)' % (container,i)):
        media_type = 'song'
    else:
        media_type = None

    item_dbid = xbmc.getInfoLabel('Container(%s).ListItemAbsolute(%s).DBID' % (dbid,i))
    url = xbmc.getInfoLabel('Container(%s).ListItemAbsolute(%s).Filenameandpath' % (dbid,i))

    playitem({'dbtype': media_type, 'dbid': item_dbid, 'item': url})


def jumptoshow_by_episode(params):
    episode_query = json_call('VideoLibrary.GetEpisodeDetails',
                    properties=['tvshowid'],
                    params={'episodeid': int(params.get('dbid'))}
                    )
    try:
        tvshow_id = str(episode_query['result']['episodedetails']['tvshowid'])
    except Exception:
        log('Could not get the TV show ID')
        return

    gotopath('videodb://tvshows/titles/%s/' % tvshow_id)


def goto(params):
    gotopath(remove_quotes(params.get('path')),params.get('target'))


def resetposition(params):
    containers = params.get('container').split('||')
    only_inactive_container = get_bool(params.get('only'),'inactive')
    current_control =xbmc.getInfoLabel('System.CurrentControlID')

    for item in containers:

        try:
            if current_control == item and only_inactive_container:
                raise Exception

            current_item = int(xbmc.getInfoLabel('Container(%s).CurrentItem' % item))
            if current_item > 1:
                current_item -= 1
                execute('Control.Move(%s,-%s)' % (item,str(current_item)))

        except Exception:
            pass


def details_by_season(params):
    season_query = json_call('VideoLibrary.GetSeasonDetails',
                        properties=season_properties,
                        params={'seasonid': int(params.get('dbid'))}
                        )

    try:
        tvshow_id = str(season_query['result']['seasondetails']['tvshowid'])
    except Exception:
        log('Show details by season: Could not get TV show ID')
        return

    tvshow_query = json_call('VideoLibrary.GetTVShowDetails',
                        properties=tvshow_properties,
                        params={'tvshowid': int(tvshow_id)}
                        )

    try:
        details = tvshow_query['result']['tvshowdetails']
    except Exception:
        log('Show details by season: Could not get TV show details')
        return

    episode = details['episode']
    watchedepisodes = details['watchedepisodes']
    unwatchedepisodes = get_unwatched(episode,watchedepisodes)

    winprop('tvshow.dbid', str(details['tvshowid']))
    winprop('tvshow.rating', str(round(details['rating'],1)))
    winprop('tvshow.seasons', str(details['season']))
    winprop('tvshow.episodes', str(episode))
    winprop('tvshow.watchedepisodes', str(watchedepisodes))
    winprop('tvshow.unwatchedepisodes', str(unwatchedepisodes))


def txtfile(params):
    prop = params.get('property')
    path = xbmc.translatePath(remove_quotes(params.get('path')))

    if os.path.isfile(path):
        log('Reading file %s' % path)

        file = open(path, 'r')
        text = file.read()
        file.close()

        if prop:
            winprop(prop,text)
        else:
            DIALOG.textviewer(remove_quotes(params.get('header')),text)

    else:
        log('Cannot find %s' % path)
        winprop(prop, clear=True)


def blurimg(params):

    image_filter(params.get('prop','output'),remove_quotes(params.get('file')),params.get('radius'))


def fontchange(params):
    font = params.get('font')
    fallback_locales = params.get('locales').split('+')

    try:
        defaultlocale = locale.getdefaultlocale()
        shortlocale = defaultlocale[0][3:].lower()

        for value in fallback_locales:
            if value == shortlocale:
                setkodisetting({'setting': 'lookandfeel.font', 'value': params.get('font')})
                DIALOG.notification('%s %s' % (value.upper(),ADDON.getLocalizedString(32004)), '%s %s' % (ADDON.getLocalizedString(32005),font))
                log('Locale %s is not supported by default font. Change to %s.' % (value.upper(),font))
                break

    except Exception:
        log('Auto font change: No system locale found')


def setinfo(params):
    dbid = params.get('dbid')
    dbtype = params.get('type')
    value = params.get('value')

    try:
        value = int(value)
    except Exception:
        pass

    if dbtype == 'movie':
        method = 'VideoLibrary.SetMovieDetails'
        key = 'movieid'
    elif dbtype == 'episode':
        method = 'VideoLibrary.SetEpisodeDetails'
        key = 'episodeid'
    elif dbtype == 'tvshow':
        method = 'VideoLibrary.SetTVShowDetails'
        key = 'tvshowid'

    json_call(method,
                params={key: int(dbid), params.get('field'): value}
                )


def split(params):
    value =  remove_quotes(params.get('value'))
    prop = params.get('prop')
    separator = remove_quotes(params.get('separator'))

    if value:
        if separator:
            value = value.split(separator)
        else:
            value = value.splitlines()

        i = 0
        for item in value:
            winprop('%s.%s' % (prop,i), item)
            i += 1

        for item in range(i,30):
            winprop('%s.%s' % (prop,i), clear=True)
            i += 1


def lookforfile(params):
    file = remove_quotes(params.get('file'))
    prop = params.get('prop','FileExists')

    if xbmcvfs.exists(file):
        winprop('%s.bool' % prop, True)
        log('File exists: %s' % file)
    else:
        winprop(prop, clear=True)
        log('File does not exist: %s' % file)


def getlocale(params):
    try:
        defaultlocale = locale.getdefaultlocale()
        shortlocale = defaultlocale[0][3:].upper()
        winprop('SystemLocale', shortlocale)
    except Exception:
        winprop('SystemLocale', clear=True)


class PlayCinema(object):

    def __init__(self, params):
        self.trailer_count = xbmc.getInfoLabel('Skin.String(TrailerCount)') if xbmc.getInfoLabel('Skin.String(TrailerCount)') != '0' else False
        self.intro_path = xbmc.getInfoLabel('Skin.String(IntroPath)')

        self.dbid = params.get('dbid')
        self.dbtype = params.get('type')

        if not self.dbid or not self.dbtype:
            for i in range(30):
                if xbmc.getInfoLabel('Container.ListItem.Label'):
                    break
                xbmc.sleep(100)

            self.dbid = xbmc.getInfoLabel('Container.ListItem.DBID')
            self.dbtype = xbmc.getInfoLabel('Container.ListItem.DBTYPE')

        if self.dbid and self.dbtype:
            self.run()
        else:
            log('Play with cinema mode: Not enough arguments')


    def run(self):
        clear_playlists()
        index = 0

        if self.trailer_count:
            movies = self.get_trailers()
            for trailer in movies:

                trailer_title = '%s (%s)' % (trailer['title'], xbmc.getLocalizedString(20410))
                trailer_rating = str(round(trailer['rating'],1))
                trailer_thumb = trailer['art'].get('landscape') or trailer['art'].get('fanart') or trailer['art'].get('poster', '')

                listitem = xbmcgui.ListItem(trailer_title)
                listitem.setInfo('video', {'Title': trailer_title, 'mediatype': 'video', 'plot': trailer.get('plot', ''), 'year': trailer.get('year', ''), 'mpaa': trailer.get('mpaa', ''), 'rating': trailer_rating})
                listitem.setArt({'thumb': trailer_thumb, 'clearlogo': trailer['art'].get('clearlogo', '')})
                VIDEOPLAYLIST.add(url=trailer['trailer'], listitem=listitem, index=index)

                log('Play with cinema mode: Adding trailer %s' % trailer_title)

                index += 1

        if self.intro_path:
            intro = self.get_intros()
            if intro:
                listitem = xbmcgui.ListItem('Intro')
                listitem.setInfo('video', {'Title': 'Intro', 'mediatype': 'video'})
                listitem.setArt({'thumb':'special://home/addons/script.embuary.helper/resources/trailer.jpg'})
                VIDEOPLAYLIST.add(url=intro, listitem=listitem, index=index)

                log('Play with cinema mode: Adding intro %s' % intro)
                index += 1


        json_call('Playlist.Add',
                    item={'%sid' % self.dbtype: int(self.dbid)},
                    params={'playlistid': 1}
                    )

        log('Play with cinema mode: Grab your popcorn')

        execute('Dialog.Close(all,true)')

        json_call('Player.Open',
                item={'playlistid': 1, 'position': 0},
                options={'shuffled': False}
                )


    def get_trailers(self):
            movies = json_call('VideoLibrary.GetMovies',
                                properties=movie_properties,
                                query_filter={'and': [{'field': 'playcount', 'operator': 'lessthan', 'value': '1'},{'field': 'hastrailer', 'operator': 'true', 'value': []}]},
                                sort={'method': 'random'}, limit=int(self.trailer_count)
                                )

            try:
                movies = movies['result']['movies']
            except KeyError:
                log('Play with cinema mode: No unwatched movies with available trailer found')
                return

            return movies


    def get_intros(self):
            dirs, files = xbmcvfs.listdir(self.intro_path)

            intros = []
            for file in files:
                if file.endswith(('.mp4', '.mkv', '.mpg', '.mpeg', '.avi', '.wmv', '.mov')):
                    intros.append(file)

            if intros:
                url = '%s%s' % (self.intro_path,random.choice(intros))
                return url

            log('Play with cinema mode: No intros found')
            return
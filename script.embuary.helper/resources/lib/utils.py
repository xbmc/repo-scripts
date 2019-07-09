#!/usr/bin/python
# coding: utf-8

########################

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
    import urllib2 as urllib
except ImportError:
    import urllib.request as urllib

from resources.lib.helper import *
from resources.lib.library import *
from resources.lib.json_map import *
from resources.lib.image import *

########################

def selectdialog(params):
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
        select_dialog = xbmcgui.Dialog()
        index = select_dialog.select(headertxt, selectionlist)

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
    dialog = xbmcgui.Dialog()
    dialog.ok(heading=headertxt, line1=bodytxt)
    del dialog


def dialogyesno(params):
    headertxt = remove_quotes(params.get('header', ''))
    bodytxt = remove_quotes(params.get('message', ''))
    yesactions = params.get('yesaction', '').split('|')
    noactions = params.get('noaction', '').split('|')

    if xbmcgui.Dialog().yesno(heading=headertxt, line1=bodytxt):
        for action in yesactions:
            execute(action)
    else:
        for action in noactions:
            execute(action)


def textviewer(params):
    headertxt = remove_quotes(params.get('header', ''))
    bodytxt = remove_quotes(params.get('message', ''))
    xbmcgui.Dialog().textviewer(headertxt, bodytxt)


def togglekodisetting(params):
    settingname = params.get('setting', '')
    value = False if visible('system.getbool(%s)' % settingname) else True

    json_call('Settings.SetSettingValue',
                params={'setting': '%s' % settingname, 'value': value}
                )


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
    enable = True if params.get('enable').lower() == 'true' else False

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
    shuffled = True if params.get('shuffle') == 'true' else False

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

    dbid = params.get('id')
    method = params.get('method')

    playlistid = 0 if params.get('type') == 'music' else 1
    shuffled = True if method == 'shuffle' else False

    if method == 'fromhere':
        method = 'Container(%s).ListItemNoWrap' % dbid
    else:
        method = 'Container(%s).ListItemAbsolute' % dbid

    for i in range(int(xbmc.getInfoLabel('Container(%s).NumItems' % dbid))):

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

    dbid = params.get('id')

    i = random.randint(1,int(xbmc.getInfoLabel('Container(%s).NumItems' % dbid)))

    if visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,movie)' % (dbid,i)):
        media_type = 'movie'
    elif visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,episode)' % (dbid,i)):
        media_type = 'episode'
    elif visible('String.IsEqual(Container(%s).ListItemAbsolute(%s).DBType,song)' % (dbid,i)):
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


def gotopath(path,target='videos'):
    execute('Dialog.Close(all,true)')
    execute('Container.Update(%s)' % path) if visible('Window.IsMedia') else execute('ActivateWindow(%s,%s,return)' % (target,path))


def resetposition(params):
    containers = params.get('container').split('||')
    only_inactive_container = True if params.get('only') == 'inactive' else False
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


def tvshow_details_by_season(params):
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
            xbmcgui.Dialog().textviewer(remove_quotes(params.get('header')),text)

    else:
        log('Cannot find %s' % path)
        winprop(prop, clear=True)


def blurimg(params):

    image_filter(params.get('prop','output'),remove_quotes(params.get('file')),params.get('radius'))


def fontchange(params):
    font = params.get('font')

    for value in params.get('locales').split('+'):

        if value in str(locale.getdefaultlocale()):
            setkodisetting({'setting': 'lookandfeel.font', 'value': params.get('font')})
            xbmcgui.Dialog().notification('%s %s' % (value.upper(),ADDON.getLocalizedString(30004)), '%s %s' % (ADDON.getLocalizedString(30005),font))
            log('Locale %s is not supported by default font. Change to %s.' % (value.upper(),font))
            break


def setinfo(params):
    dbid = params.get('dbid')
    dbtype = params.get('type')

    try:
        value = int(params.get('value'))
    except Exception:
        value = params.get('value')

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

class PlayCinema(object):

    def __init__(self, params):

        self.trailer_count = xbmc.getInfoLabel('Skin.String(TrailerCount)') if not xbmc.getInfoLabel('Skin.String(TrailerCount)') == '0' else ''
        self.intro_path = xbmc.getInfoLabel('Skin.String(IntroPath)')

        self.dbid = params.get('dbid')
        self.dbtype = params.get('type')
        self.item_title = remove_quotes(params.get('title'))

        if not self.dbid or not self.item_title or not self.dbtype:
            for i in range(30):

                if xbmc.getInfoLabel('Container.ListItem.Label'):
                    break
                xbmc.sleep(100)

            self.dbid = xbmc.getInfoLabel('Container.ListItem.DBID')
            self.item_title = xbmc.getInfoLabel('Container.ListItem.Label')
            self.dbtype = xbmc.getInfoLabel('Container.ListItem.DBTYPE')

        if self.dbid and self.item_title and self.dbtype:
            log('Play with cinema mode: %s' % self.item_title)
            self.run()
        else:
            log('Play with cinema mode: Not enough arguments')


    def run(self):
        index = 0
        VIDEOPLAYLIST.clear()

        if self.trailer_count:
            trailers = self.get_trailers()
            for trailer in trailers:

                trailer_title = '%s (%s)' % (trailer['title'], xbmc.getLocalizedString(20410))
                trailer_rating = str(round(trailer['rating'],1))
                thumbnailImage = trailer['art'].get('landscape') or trailer['art'].get('fanart') or trailer['art'].get('poster', '')

                listitem = xbmcgui.ListItem(trailer_title)
                listitem.setInfo('video', {'Title': trailer_title, 'mediatype': 'video', 'plot': trailer.get('plot', ''), 'year': trailer.get('year', ''), 'mpaa': trailer.get('mpaa', ''), 'rating': trailer_rating})
                listitem.setArt({'thumb':thumbnailImage, 'clearlogo': trailer['art'].get('clearlogo', '')})
                VIDEOPLAYLIST.add(url=trailer['trailer'], listitem=listitem, index=index)

                log('Play with cinema mode: Adding trailer %s' % trailer_title)

                index += 1

        if self.intro_path:
            intro = self.get_intros()
            if intro:
                intro_title = '%s (Intro)' % (self.item_title)

                listitem = xbmcgui.ListItem(intro_title)
                listitem.setInfo('video', {'Title': intro_title, 'mediatype': 'video'})
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
                                query_filter={'field': 'playcount', 'operator': 'lessthan', 'value': '1'},
                                sort={'method': 'random'}, limit=int(self.trailer_count)
                                )

            try:
                movies = movies['result']['movies']
            except KeyError:
                return

            return movies

    def get_intros(self):

            dirs, files = xbmcvfs.listdir(self.intro_path)

            intros = []
            for file in files:
                if file.endswith(('.mp4', '.mkv', '.mpg', '.mpeg', '.avi', '.wmv', '.mov', '.flv')):
                    intros.append(file)

            if intros:
                random.shuffle(intros)
                self.intro_path += intros[0]
                return self.intro_path

            return intros
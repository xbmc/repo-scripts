#!/usr/bin/python
# coding: utf-8

#################################################################################################

import xbmc
import xbmcgui
import xbmcvfs
import random
import os

from resources.lib.helper import *
from resources.lib.json_map import *

#################################################################################################

class CinemaMode(object):
    def __init__(self,dbid,dbtype):
        self.trailer_count = xbmc.getInfoLabel('Skin.String(TrailerCount)') if xbmc.getInfoLabel('Skin.String(TrailerCount)') != '0' else False
        self.intro_path = xbmc.getInfoLabel('Skin.String(IntroPath)')

        self.dbid = dbid
        self.dbtype = dbtype

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
                trailer_rating = str(round(trailer['rating'], 1))
                trailer_thumb = trailer['art'].get('landscape') or trailer['art'].get('fanart') or trailer['art'].get('poster', '')

                listitem = xbmcgui.ListItem(trailer_title, offscreen=True)
                listitem.setInfo('video', {'Title': trailer_title,
                                           'mediatype': 'video',
                                           'plot': trailer.get('plot', ''),
                                           'year': trailer.get('year', ''),
                                           'mpaa': trailer.get('mpaa', ''),
                                           'rating': trailer_rating
                                           })

                listitem.setArt({'thumb': trailer_thumb,
                                 'clearlogo': trailer['art'].get('clearlogo') or trailer['art'].get('logo') or ''
                                 })

                VIDEOPLAYLIST.add(url=trailer['trailer'], listitem=listitem, index=index)
                log('Play with cinema mode: Adding trailer %s' % trailer_title)

                index += 1

        if self.intro_path:
            intro = self.get_intros()
            if intro:
                listitem = xbmcgui.ListItem('Intro', offscreen=True)
                listitem.setInfo('video', {'Title': 'Intro',
                                           'mediatype': 'video'}
                                           )

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
                           properties=JSON_MAP['movie_properties'],
                           query_filter={'and': [{'field': 'playcount', 'operator': 'lessthan', 'value': '1'}, {'field': 'hastrailer', 'operator': 'true', 'value': []}]},
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
            url = os.path.join(self.intro_path, random.choice(intros))
            return url

        log('Play with cinema mode: No intros found')
        return
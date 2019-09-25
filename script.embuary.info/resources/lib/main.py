#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcgui

from resources.lib.helper import *
from resources.lib.utils import *
from resources.lib.person import *
from resources.lib.video import *
from resources.lib.season import *

########################

class TheMovieDB(object):
    def __init__(self,call,params):
        self.window_stack = []
        self.dialog_cache = {}
        self.call = call
        self.tmdb_id = params.get('tmdb_id')
        self.season = params.get('season')
        self.query = remove_quotes(params.get('query'))
        self.query_year = params.get('year')
        self.external_id = params.get('external_id')

        winprop('script.embuary.info-language_code', DEFAULT_LANGUAGE)
        winprop('script.embuary.info-country_code', COUNTRY_CODE)

        busydialog()

        if self.external_id or self.query:
            self.tmdb_id = self.find_id()

        if self.tmdb_id:
            self.call_params = {}

            local_media = get_local_media()
            self.call_params['local_shows'] = local_media['shows']
            self.call_params['local_movies'] = local_media['movies']

            self.entry_point()

        busydialog(close=True)


    ''' Search for tmdb_id based one a query string or external ID (IMDb or TVDb)
    '''
    def find_id(self):
        if self.external_id:
            result = tmdb_find(self.call,self.external_id)
        else:
            if ' / ' in self.query:
                query_values = self.query.split(' / ')
                position = tmdb_select_dialog_small(query_values)
                if position < 0:
                    return ''
                else:
                    self.query = query_values[position]

            result = tmdb_search(self.call,self.query,self.query_year)

        try:
            if len(result) > 1:
                position = tmdb_select_dialog(result,self.call)
                if position < 0:
                    raise Exception
            else:
                position = 0

            tmdb_id = result[position]['id']

        except Exception:
            return ''

        return tmdb_id


    ''' Collect all data by the tmdb_id and build the dialogs.
    '''
    def entry_point(self):
        self.call_params['call'] = self.call
        self.call_params['tmdb_id'] = self.tmdb_id
        self.call_params['season'] = self.season
        self.request = self.call + str(self.tmdb_id)

        busydialog()

        if self.call == 'person':
            dialog = self.fetch_person()
        elif self.call == 'tv' and self.season:
            dialog = self.fetch_season()
        elif self.call == 'movie' or self.call == 'tv':
            dialog = self.fetch_video()

        busydialog(close=True)

        ''' Open next dialog if information has been found. If not open the previous dialog again.
        '''
        if dialog:
            self.dialog_cache[self.request] = dialog
            self.dialog_manager(dialog)

        elif self.window_stack:
            self.dialog_history()

        else:
            self.quit()

    def fetch_person(self):
        data = TMDBPersons(self.call_params)
        if not data['person']:
            return

        dialog = DialogPerson('script-embuary-person.xml', ADDON_PATH, 'default', '1080i',
                            person=data['person'],
                            movies=data['movies'],
                            tvshows=data['tvshows'],
                            images=data['images'],
                            tmdb_id=self.tmdb_id
                            )
        return dialog

    def fetch_video(self):
        data = TMDBVideos(self.call_params)
        if not data['details']:
            return

        dialog = DialogVideo('script-embuary-video.xml', ADDON_PATH, 'default', '1080i',
                            details=data['details'],
                            cast=data['cast'],
                            crew=data['crew'],
                            similar=data['similar'],
                            youtube=data['youtube'],
                            backdrops=data['backdrops'],
                            posters=data['posters'],
                            collection=data['collection'],
                            seasons=data['seasons'],
                            tmdb_id=self.tmdb_id
                            )
        return dialog

    def fetch_season(self):
        data = TMDBSeasons(self.call_params)
        if not data['details']:
            return

        dialog = DialogSeason('script-embuary-video.xml', ADDON_PATH, 'default', '1080i',
                            details=data['details'],
                            cast=data['cast'],
                            gueststars=data['gueststars'],
                            posters=data['posters'],
                            tmdb_id=self.tmdb_id
                            )
        return dialog


    ''' Dialog handler. Creates the window history, reopens dialogs from a stack
        or cache and is responsible for keeping the script alive.
    '''
    def dialog_manager(self,dialog):
        dialog.doModal()

        try:
            next_id = dialog['id']
            next_call = dialog['call']
            next_season = dialog['season']

            if next_call == 'back':
                self.dialog_history()

            if next_call == 'close':
                raise Exception

            if not next_id or not next_call:
                raise Exception

            self.window_stack.append(dialog)
            self.tmdb_id = next_id
            self.call = next_call
            self.season = next_season
            self.request = next_call + str(next_id) + str(next_season)

            if self.dialog_cache.get(self.request):
                dialog = self.dialog_cache[self.request]
                self.dialog_manager(dialog)
            else:
                self.entry_point()

        except Exception:
            self.quit()

    def dialog_history(self):
        if self.window_stack:
            dialog = self.window_stack.pop()
            self.dialog_manager(dialog)
        else:
            self.quit()

    def quit(self):
        del self.call_params
        del self.window_stack
        del self.dialog_cache
        quit()


''' Person dialog
'''
class DialogPerson(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self.first_load = True
        self.action = {}

        self.tmdb_id = kwargs['tmdb_id']
        self.person = kwargs['person']
        self.movies = kwargs['movies']
        self.tvshows = kwargs['tvshows']
        self.images = kwargs['images']

    def __getitem__(self,key):
        return self.action[key]

    def __setitem__(self,key,value):
        self.action[key] = value

    def onInit(self):
        if self.first_load:
            self.add_items()

    def add_items(self):
        self.first_load = False

        self.cont0 = self.getControl(10051)
        self.cont0.addItems(self.person)
        self.cont1 = self.getControl(10052)
        self.cont1.addItems(self.movies)
        self.cont2 = self.getControl(10053)
        self.cont2.addItems(self.tvshows)
        self.cont3 = self.getControl(10054)
        self.cont3.addItems(self.images)

    def onAction(self,action):
        if action.getId() in [92,10]:
            self.action['id'] = ''
            self.action['season'] = ''
            self.action['call'] = 'back' if action.getId() == 92 else 'close'
            self.quit()

    def onClick(self,controlId):
        next_id = xbmc.getInfoLabel('Container(%s).ListItem.Property(id)' % controlId)
        next_call = xbmc.getInfoLabel('Container(%s).ListItem.Property(call)' % controlId)

        if next_call in ['person','movie','tv'] and next_id:
            self.action['id'] = next_id
            self.action['call'] = next_call
            self.action['season'] = ''
            self.quit()

        elif next_call == 'image':
            FullScreenImage(controlId)

    def quit(self):
        close_action = self.getProperty('onclose')
        onback_action = self.getProperty('onback_%s' % self.getFocusId())

        if self.action.get('call') == 'back' and onback_action:
            execute(onback_action)
        else:
            if close_action:
                execute(close_action)
            self.close()


''' Show & movie dialog
'''
class DialogVideo(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self.first_load = True
        self.action = {}

        self.tmdb_id = kwargs['tmdb_id']
        self.details = kwargs['details']
        self.cast = kwargs['cast']
        self.crew = kwargs['crew']
        self.similar = kwargs['similar']
        self.youtube = kwargs['youtube']
        self.backdrops = kwargs['backdrops']
        self.posters = kwargs['posters']
        self.seasons = kwargs['seasons']
        self.collection = kwargs['collection']

    def __getitem__(self,key):
        return self.action[key]

    def __setitem__(self,key,value):
        self.action[key] = value

    def onInit(self):
        if self.first_load:
            self.add_items()

    def add_items(self):
        self.first_load = False
        self.cont0 = self.getControl(10051)
        self.cont0.addItems(self.details)
        self.cont1 = self.getControl(10052)
        self.cont1.addItems(self.cast)
        self.cont2 = self.getControl(10053)
        self.cont2.addItems(self.similar)
        self.cont3 = self.getControl(10054)
        self.cont3.addItems(self.youtube)
        self.cont4 = self.getControl(10055)
        self.cont4.addItems(self.backdrops)
        self.cont5 = self.getControl(10056)
        self.cont5.addItems(self.crew)
        self.cont6 = self.getControl(10057)
        self.cont6.addItems(self.collection)
        self.cont7 = self.getControl(10058)
        self.cont7.addItems(self.seasons)
        self.cont8 = self.getControl(10059)
        self.cont8.addItems(self.posters)

    def onAction(self,action):
        if action.getId() in [92,10]:
            self.action['id'] = ''
            self.action['season'] = ''
            self.action['call'] = 'back' if action.getId() == 92 else 'close'
            self.quit()

    def onClick(self,controlId):
        next_id = xbmc.getInfoLabel('Container(%s).ListItem.Property(id)' % controlId)
        next_call = xbmc.getInfoLabel('Container(%s).ListItem.Property(call)' % controlId)
        next_season = xbmc.getInfoLabel('Container(%s).ListItem.Property(call_season)' % controlId)

        if next_call in ['person','movie','tv'] and next_id:
            if next_id != str(self.tmdb_id) or next_season:
                self.action['id'] = next_id
                self.action['call'] = next_call
                self.action['season'] = next_season
                self.quit()

        elif next_call == 'image':
            FullScreenImage(controlId)

        elif next_call == 'youtube':
            self.action['call'] = 'close'
            execute('Dialog.Close(all)')
            xbmc.Player().play('plugin://plugin.video.youtube/play/?video_id=%s' % xbmc.getInfoLabel('Container(%s).ListItem.Property(ytid)' % controlId))
            self.quit()

    def quit(self):
        close_action = self.getProperty('onclose')
        onback_action = self.getProperty('onback_%s' % self.getFocusId())

        if self.action.get('call') == 'back' and onback_action:
            execute(onback_action)
        else:
            if close_action:
                execute(close_action)
            self.close()


''' Season dialog
'''
class DialogSeason(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self.first_load = True
        self.action = {}

        self.tmdb_id = kwargs['tmdb_id']
        self.details = kwargs['details']
        self.cast = kwargs['cast']
        self.gueststars = kwargs['gueststars']
        self.posters = kwargs['posters']

    def __getitem__(self,key):
        return self.action[key]

    def __setitem__(self,key,value):
        self.action[key] = value

    def onInit(self):
        if self.first_load:
            self.add_items()

    def add_items(self):
        self.first_load = False
        self.cont0 = self.getControl(10051)
        self.cont0.addItems(self.details)
        self.cont1 = self.getControl(10052)
        self.cont1.addItems(self.cast)
        self.cont2 = self.getControl(10056)
        self.cont2.addItems(self.gueststars)
        self.cont3 = self.getControl(10059)
        self.cont3.addItems(self.posters)

    def onAction(self,action):
        if action.getId() in [92,10]:
            self.action['id'] = ''
            self.action['season'] = ''
            self.action['call'] = 'back' if action.getId() == 92 else 'close'
            self.quit()

    def onClick(self,controlId):
        next_id = xbmc.getInfoLabel('Container(%s).ListItem.Property(id)' % controlId)
        next_call = xbmc.getInfoLabel('Container(%s).ListItem.Property(call)' % controlId)

        if next_call in ['person'] and next_id:
            self.action['id'] = next_id
            self.action['call'] = next_call
            self.action['season'] = ''
            self.quit()

        elif next_call == 'image':
            FullScreenImage(controlId)

    def quit(self):
        close_action = self.getProperty('onclose')
        onback_action = self.getProperty('onback_%s' % self.getFocusId())

        if self.action.get('call') == 'back' and onback_action:
            execute(onback_action)
        else:
            if close_action:
                execute(close_action)
            self.close()


''' Slideshow dialog
'''
class FullScreenImage(object):
    def __init__(self,controlId):
        slideshow = []
        for i in range(int(xbmc.getInfoLabel('Container(%s).NumItems' % controlId))):
            slideshow.append(xbmc.getInfoLabel('Container(%s).ListItemAbsolute(%s).Art(thumb)' % (controlId,i)))

        dialog = self.ShowImage('script-embuary-image.xml', ADDON_PATH, 'default', '1080i', slideshow=slideshow, position=xbmc.getInfoLabel('Container(%s).CurrentItem' % controlId))
        dialog.doModal()
        del dialog

    class ShowImage(xbmcgui.WindowXMLDialog):
        def __init__(self,*args,**kwargs):
            self.position = int(kwargs['position']) - 1
            self.slideshow = list()
            for item in kwargs['slideshow']:
                list_item = xbmcgui.ListItem(label='')
                list_item.setArt({'icon': item})
                self.slideshow.append(list_item)

        def onInit(self):
            self.cont = self.getControl(1)
            self.cont.addItems(self.slideshow)
            self.cont.selectItem(self.position)
            self.setFocusId(2)
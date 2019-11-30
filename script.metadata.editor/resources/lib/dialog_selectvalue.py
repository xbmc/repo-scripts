#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.functions import *

########################

class SelectValue(object):
    def __init__(self,params,editor=False):
        self.dbid = params.get('dbid')
        self.dbtype = params.get('type')
        self.dbkey = params.get('key')
        self.editor = editor

        if self.dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
            self.library = 'Video'
            self.nfo_support = True
        else:
            self.library = 'Audio'
            self.nfo_support = False

        self.method_details = '%sLibrary.Get%sDetails' % (self.library, self.dbtype)
        self.method_setdetails = '%sLibrary.Set%sDetails' % (self.library, self.dbtype)
        self.param = '%sid' % self.dbtype
        self.key_details = '%sdetails' % self.dbtype
        self.dbkey_details = '%ss' % self.dbkey

        self.all_values = []
        self.duplicate_handler = []

        self.init()

    def __str__(self):
        return str(self.modified)

    def init(self):
        if self.dbkey == 'genre':
            if self.dbtype in ['movie', 'tvshow', 'season', 'episode']:
                self.available_video_values()
            else:
                self.available_audio_values()

        elif self.dbkey == 'tag':
            if self.dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
                self.available_video_values()
            else:
                self.available_audio_values()

        self.current_values()
        self.select_dialog()

        if not self.editor:
            self.update_data()
            reload_widgets()

    def current_values(self):
        result = json_call(self.method_details,
                           properties=[self.dbkey, 'file'] if self.library == 'Video' else [self.dbkey],
                           params={self.param: int(self.dbid)}
                           )

        result = result['result'][self.key_details]

        self.values = result.get(self.dbkey, [])
        self.file = result.get('file')

        # also show musicvideo values if not listed for audio returns
        if self.dbtype == 'musicvideo' and self.dbkey == 'genre':
            for item in self.values:
                if item not in self.all_values:
                    self.all_values.append(item)

        # for regular library arrays that only can be fetched on item base
        if not self.all_values:
            self.all_values = self.values

    def available_video_values(self):
        self._json_query(type='movie')
        self._json_query(type='tvshow')

        if self.dbkey != 'genre':
            self._json_query(type='musicvideo')

    def available_audio_values(self):
        self._json_query(library='Audio')

        if self.dbkey == 'genre':
            self._json_query(library='Video', type='musicvideo')

    def select_dialog(self):
        preselectlist = []
        self.modified = []

        self.values.sort()
        self.all_values.sort()

        for item in self.values:
            preselectlist.append(self.all_values.index(item))

        selectdialog = DIALOG.multiselect(ADDON.getLocalizedString(32002), self.all_values, preselect=preselectlist)

        if selectdialog == -1:
            self.modified = []

        elif selectdialog is not None:
            for index in selectdialog:
                self.modified.append(self.all_values[index])

        else:
            self.modified = self.values

    def update_data(self):
        json_call(self.method_setdetails,
                  params={self.param: int(self.dbid), self.dbkey: self.modified},
                  debug=LOG_JSON
                  )

        if self.nfo_support and self.file:
            if self.dbkey == 'tag':
                # Respect Emby favourites <isuserfavorite>
                isuserfavorite = 'false'
                for tag in self.modified:
                    if tag in ['Movie Watchlist', 'TV Show Watchlist', 'Music Video Watchlist', 'Favorite movies', 'Favorite tvshows']:
                        isuserfavorite = 'true'
                        break

                self.dbkey = [self.dbkey, 'isuserfavorite']
                self.modified = [self.modified, isuserfavorite]

            update_nfo(file=self.file,
                       elem=self.dbkey,
                       value=self.modified,
                       dbtype=self.dbtype,
                       dbid=self.dbid)

    def _json_query(self,library=None,type=None):
        if library is None:
            library = self.library

        if type is not None:
            params = {'type': type}
        else:
            params = None

        result = json_call('%sLibrary.Get%ss' % (library, self.dbkey),
                           properties=['title'],
                           params=params
                           )

        try:
            for item in result['result'][self.dbkey_details]:
                label = item['label']
                if label not in self.duplicate_handler:
                    self.all_values.append(label)
                    self.duplicate_handler.append(label)

        except KeyError:
            pass
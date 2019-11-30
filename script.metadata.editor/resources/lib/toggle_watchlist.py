#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.functions import *

########################

class ToggleWatchlist(object):
    def __init__(self,params):
        self.dbid = params.get('dbid')
        self.dbtype = params.get('type')

        self.method_details = 'VideoLibrary.Get%sDetails' % self.dbtype
        self.method_setdetails = 'VideoLibrary.Set%sDetails' % self.dbtype
        self.param = '%sid' % self.dbtype
        self.key_details = '%sdetails' % self.dbtype
        self.tag = 'Watchlist'

        self.init()

    def init(self):
        self.check_tag()
        self.update_info()

    def check_tag(self):
        result = json_call(self.method_details,
                           properties=['tag', 'file'],
                           params={self.param: int(self.dbid)}
                           )

        result = result['result'][self.key_details]

        self.tag_list = result.get('tag', [])
        self.is_fav = True if self.tag in self.tag_list else False
        self.file = result.get('file')

    def update_info(self):
        if not self.is_fav:
            isuserfavorite = 'true'
            self.tag_list.append(self.tag)
        else:
            isuserfavorite = 'false'
            self.tag_list.remove(self.tag)

        json_call(self.method_setdetails,
                  params={self.param: int(self.dbid), 'tag': self.tag_list},
                  debug=LOG_JSON
                  )

        if self.file:
            # Respect Emby favourites <isuserfavorite>
            if ('Favorite movies' in self.tag_list) or ('Favorite tvshows' in self.tag_list):
                isuserfavorite = 'true'

            update_nfo(file=self.file,
                       elem=['tag', 'isuserfavorite'],
                       value=[self.tag_list, isuserfavorite],
                       dbtype=self.dbtype,
                       dbid=self.dbid)

        reload_widgets()
#!/usr/bin/python
# coding: utf-8

#################################################################################################

import xbmc
import sys

from resources.lib.helper import *
from resources.lib.json_map import *
from resources.lib.dialog_metadata import *
from resources.lib.dialog_selectvalue import *
from resources.lib.toggle_watchlist import *
from resources.lib.rating_updater import *

#################################################################################################

class ContextMenu(object):
    def __init__(self,dbid,dbtype):
        self.dbid = dbid
        self.dbtype = dbtype

        if self.dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
            library = 'Video'
        else:
            library = 'Audio'

        self.method_details = '%sLibrary.Get%sDetails' % (library, self.dbtype)
        self.param = '%sid' % self.dbtype
        self.key_details = '%sdetails' % self.dbtype
        self.properties = eval('%s_properties' % self.dbtype)

        self.details = self.get_details()

        self.menu()

    def get_details(self):
        json_query = json_call(self.method_details,
                               properties=self.properties,
                               params={self.param: int(self.dbid)}
                               )
        try:
            result = json_query['result'][self.key_details]
            return result

        except KeyError:
            return

    def menu(self):
        itemlist = [ADDON.getLocalizedString(32010)]

        if 'genre' in self.details and self.dbtype != 'song':
            itemlist.append(ADDON.getLocalizedString(32004))

        if 'tag' in self.details:
            itemlist.append(ADDON.getLocalizedString(32003))

            if 'Watchlist' in self.details.get('tag'):
                itemlist.append(ADDON.getLocalizedString(32008))
            else:
                itemlist.append(ADDON.getLocalizedString(32009))

        if self.dbtype in ['movie', 'tvshow', 'episode']:
            itemlist.append(ADDON.getLocalizedString(32039))

        if len(itemlist) > 1:
            contextdialog = DIALOG.contextmenu(itemlist)

            if contextdialog == 0:
                EditDialog({'dbid': self.dbid, 'type': self.dbtype})

            elif contextdialog == 1:
                if self.dbtype == 'episode':
                    UpdateRating({'dbid': self.dbid, 'type': self.dbtype})

                else:
                    SelectValue({'dbid': self.dbid, 'type': self.dbtype, 'key': 'genre'})

            elif contextdialog == 2:
                SelectValue({'dbid': self.dbid, 'type': self.dbtype, 'key': 'tag'})

            elif contextdialog == 3:
                ToggleWatchlist({'dbid': self.dbid, 'type': self.dbtype})

            elif contextdialog == 4:
                UpdateRating({'dbid': self.dbid, 'type': self.dbtype})

            else:
                return

        else:
            EditDialog({'dbid': self.dbid, 'type': self.dbtype})


if __name__ == "__main__":
    listitem = sys.listitem.getVideoInfoTag()
    dbid = listitem.getDbId()
    dbtype = listitem.getMediaType()

    if not dbid or not dbtype:
        listitem = sys.listitem.getMusicInfoTag()
        dbid = listitem.getDbId()
        dbtype = listitem.getMediaType()

    ContextMenu(dbid, dbtype)
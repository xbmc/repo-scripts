#!/usr/bin/python
# coding: utf-8

#################################################################################################

import xbmc
import sys

from resources.lib.helper import *
from resources.lib.json_map import *
from resources.lib.editor import *
from resources.lib.rating_updater import *

#################################################################################################

class ContextMenu(object):
    def __init__(self,dbid,dbtype):
        self.dbid = dbid
        self.dbtype = dbtype

        db = Database(self.dbid, self.dbtype)
        getattr(db, self.dbtype)()
        self.details = db.result().get(self.dbtype)[0]

        itemlist, actionlist = self._generate_menu()

        if len(itemlist) > 1:
            contextdialog = DIALOG.contextmenu(itemlist)
            if contextdialog >= 0:
                self._exec(actionlist[contextdialog])

        else:
            self._exec(actionlist[0])

    def _generate_menu(self):
        if self.dbtype in ['movie', 'tvshow']:
            watchlist_label = ADDON.getLocalizedString(32008) if 'Watchlist' in self.details.get('tag') else ADDON.getLocalizedString(32009)
            menu = [ADDON.getLocalizedString(32010), ADDON.getLocalizedString(32004), ADDON.getLocalizedString(32003), watchlist_label, ADDON.getLocalizedString(32039)]
            actions = [0, 1, 2, 3, 4]

        elif self.dbtype == 'episode':
            menu = [ADDON.getLocalizedString(32010), ADDON.getLocalizedString(32039)]
            actions = [0, 4]

        elif self.dbtype in ['artist', 'album']:
            menu = [ADDON.getLocalizedString(32010), ADDON.getLocalizedString(32004)]
            actions = [0, 1]

        else:
            menu = [ADDON.getLocalizedString(32010)]
            actions = [0]

        if ADDON.getSettingBool('nfo_updating') and self.dbtype in ['movie', 'tvshow', 'episode']:
            menu.insert(-1, ADDON.getLocalizedString(32046))
            actions.insert(-1, 5)

        return menu, actions

    def _exec(self,action):
        editor = EditDialog(dbid=self.dbid, dbtype=self.dbtype)

        if action == 0:
            editor.editor()

        elif action == 1:
            editor.set(key='genre', type='select')

        elif action == 2:
            editor.set(key='tag', type='select')

        elif action == 3:
            editor.set(key='tag', type='watchlist')

        elif action == 4 :
            update_ratings(dbid=self.dbid, dbtype=self.dbtype)

        elif action == 5:
            winprop('updatenfo.bool', True)
            update_nfo(dbid=self.dbid, dbtype=self.dbtype, details=self.details)
            winprop('updatenfo', clear=True)


if __name__ == "__main__":
    listitem = sys.listitem.getVideoInfoTag()
    dbid = listitem.getDbId()
    dbtype = listitem.getMediaType()

    if not dbid or not dbtype:
        listitem = sys.listitem.getMusicInfoTag()
        dbid = listitem.getDbId()
        dbtype = listitem.getMediaType()

    ContextMenu(dbid, dbtype)
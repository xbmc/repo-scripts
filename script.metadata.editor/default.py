#!/usr/bin/python

########################

from resources.lib.helper import *
from resources.lib.editor import *
from resources.lib.rating_updater import *
from context import *

########################

class Main:
    def __init__(self):
        self.action = None
        self._parse_argv()
        self.dbid = self.params.get('dbid', xbmc.getInfoLabel('ListItem.DBID'))
        self.dbtype = self.params.get('type', xbmc.getInfoLabel('ListItem.DBType'))
        self.option = self.params.get('option')

        menu_items = [ADDON.getLocalizedString(32038), ADDON.getLocalizedString(32037), ADDON.getLocalizedString(32036), ADDON.getLocalizedString(32045)]
        menu_actions = [['movies', 'tvshows', 'episodes'], 'movies', 'tvshows', 'episodes']

        if not self.action and not self.dbid and not self.dbtype and not self.option:
            updateselector = DIALOG.contextmenu(menu_items)
            if updateselector >= 0:
                update_ratings(dbtype=menu_actions[updateselector])

        elif self.action == 'updaterating' and self.option:
            content = []
            for i in self.option.split('+'):
                if i in ['movies', 'tvshows', 'episodes']:
                    content.append(i)

            if content:
                update_ratings(dbtype=content)

        elif self.dbid and self.dbtype:
            if self.action == 'updaterating':
                if self.dbtype in ['movie', 'tvshow', 'episode']:
                    update_ratings(dbid=self.dbid, dbtype=self.dbtype)

                elif not self.dbtype:
                    update_ratings(dbtype=menu_actions[0])

                elif self.dbtype in menu_actions:
                    update_ratings(dbtype=menu_actions[menu_actions.index(self.dbtype)])

                else:
                    DIALOG.ok(xbmc.getLocalizedString(257), ADDON.getLocalizedString(32049) + '.[CR]ID: ' + str(self.dbid) +  ' - ' + ADDON.getLocalizedString(32051) + ': ' + str(self.dbtype))

            if self.action == 'togglewatchlist':
                self._write(key='tag', valuetype='watchlist')

            elif self.action == 'setgenre':
                self._write(key='genre', valuetype='select')

            elif self.action == 'settags':
                self._write(key='tag', valuetype='select')

            elif self.action == 'setuserrating':
                self._write(key='userrating', valuetype='userrating')

            elif self.action == 'updatenfo':
                winprop('updatenfo.bool', True)
                update_nfo(dbid=self.dbid, dbtype=self.dbtype, forced=True)
                winprop('updatenfo', clear=True)

            elif self.action == 'contextmenu':
                ContextMenu(dbid=self.dbid, dbtype=self.dbtype)

            else:
                self._editor()

    def _parse_argv(self):
        args = sys.argv
        for arg in args:
            if arg == ADDON_ID:
                continue

            if arg.startswith('action='):
                self.action = arg[7:].lower()
            else:
                try:
                    self.params[arg.split("=")[0].lower()] = "=".join(arg.split("=")[1:]).strip()
                except:
                    self.params = {}

    def _write(self,key,valuetype):
        editor = EditDialog(dbid=self.dbid, dbtype=self.dbtype)
        editor.set(key=key, type=valuetype)

    def _editor(self):
        editor = EditDialog(dbid=self.dbid, dbtype=self.dbtype)
        editor.editor()


if __name__ == '__main__':
    if winprop('UpdatingRatings.bool'):
        if DIALOG.yesno(xbmc.getLocalizedString(14117), ADDON.getLocalizedString(32050)):
            winprop('CancelRatingUpdater.bool', True)
            quit()
    Main()

#!/usr/bin/python

########################

from resources.lib.helper import *
from resources.lib.dialog_metadata import *
from resources.lib.dialog_selectvalue import *
from resources.lib.toggle_watchlist import *
from resources.lib.rating_updater import *

########################

class Main:
    def __init__(self):
        self.action = False
        self._parse_argv()
        dbid = self.params.get('dbid')
        dbtype = self.params.get('type')

        if not dbid and not dbtype and not self.action:
            omdb_msg = self._omdb_msg()
            if not omdb_msg:
                return

            if not winprop('UpdatingRatings.bool'):
                menuitems = [ADDON.getLocalizedString(32038), ADDON.getLocalizedString(32037), ADDON.getLocalizedString(32036), ADDON.getLocalizedString(32045)]
            else:
                menuitems = [ADDON.getLocalizedString(32041)]

            updateselector = DIALOG.contextmenu(menuitems)

            if updateselector == 0:
                if not winprop('UpdatingRatings.bool'):
                    UpdateAllRatings({'type': 'movie'})
                    UpdateAllRatings({'type': 'tvshow'})
                    UpdateAllRatings({'type': 'episode'})

                else:
                    winprop('CancelRatingUpdater.bool', True)

            elif updateselector == 1:
                UpdateAllRatings({'type': 'movie'})

            elif updateselector == 2:
                UpdateAllRatings({'type': 'tvshow'})

            elif updateselector == 3:
                UpdateAllRatings({'type': 'episode'})

        elif self.action == 'updaterating':
            omdb_msg = self._omdb_msg()
            if not omdb_msg:
                return

            if not dbtype:
                UpdateAllRatings({'type': 'movie'})
                UpdateAllRatings({'type': 'tvshow'})
                UpdateAllRatings({'type': 'episode'})

            elif dbtype and not dbid:
                UpdateAllRatings({'type': dbtype})

            else:
                UpdateRating({'dbid': dbid, 'type': dbtype})

        elif self.action == 'togglewatchlist':
            ToggleWatchlist({'dbid': dbid, 'type': dbtype})

        elif self.action == 'setgenre':
            SelectValue({'dbid': dbid, 'type': dbtype, 'key': 'genre'})

        elif self.action == 'settags':
            SelectValue({'dbid': dbid, 'type': dbtype, 'key': 'tag'})

        else:
            EditDialog(self.params)

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

    def _omdb_msg(self):
        if not ADDON.getSetting('omdb_api_key'):
            if not DIALOG.yesno(xbmc.getLocalizedString(14117), ADDON.getLocalizedString(32035)):
                return False
        return True

if __name__ == '__main__':
    Main()

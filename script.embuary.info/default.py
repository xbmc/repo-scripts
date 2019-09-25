#!/usr/bin/python

########################

import xbmcgui

from resources.lib.helper import *
from resources.lib.main import *

########################

class Main:

    def __init__(self):
        self.call = False
        self._parse_argv()

        if self.call:
            TheMovieDB(self.call,self.params)
        else:
            call = DIALOG.select(ADDON.getLocalizedString(32005), [ADDON.getLocalizedString(32004), xbmc.getLocalizedString(20338), xbmc.getLocalizedString(20364)])
            if call == 0:
                call = 'person'
            elif call == 1:
                call = 'movie'
            elif call == 2:
                call = 'tv'
            else:
                quit()

            query = DIALOG.input(xbmc.getLocalizedString(19133), type=xbmcgui.INPUT_ALPHANUM)
            TheMovieDB(call,{'query': query})


    def _parse_argv(self):
        args = sys.argv

        for arg in args:
            if arg == ADDON_ID:
                continue
            if arg.startswith('call='):
                self.call = arg[5:].lower()
            else:
                try:
                    self.params[arg.split("=")[0].lower()] = "=".join(arg.split("=")[1:]).strip()
                except:
                    self.params = {}


if __name__ == "__main__":
    Main()

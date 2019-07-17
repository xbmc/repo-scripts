#!/usr/bin/python

########################

import xbmcgui

from resources.lib.helper import *
from resources.lib.utils import *

########################

class Main:

    def __init__(self):
        self._parse_argv()
        if self.action:
            self.getactions()
        else:
            DIALOG.ok(ADDON.getLocalizedString(32000), ADDON.getLocalizedString(32001))

    def _parse_argv(self):
        args = sys.argv
        self.action = []
        for arg in args:
            if arg == 'script.embuary.helper':
                continue
            if arg.startswith('action='):
                self.action.append(arg[7:])
            else:
                try:
                    self.params[arg.split("=")[0].lower()] = "=".join(arg.split("=")[1:]).strip()
                except:
                    self.params = {}
                    pass

    def getactions(self):
        for action in self.action:
            if action == 'playitem':
                playitem(self.params)
            elif action == 'goto':
                goto(self.params)
            elif action == 'textviewer':
                textviewer(self.params)
            elif action == 'dialogok':
                dialogok(self.params)
            elif action == 'dialogyesno':
                dialogyesno(self.params)
            elif action == 'setkodisetting':
                setkodisetting(self.params)
            elif action == 'togglekodisetting':
                togglekodisetting(self.params)
            elif action == 'createselect':
                selectdialog(self.params)
            elif action == 'jumptoshow_by_episode':
                jumptoshow_by_episode(self.params)
            elif action == 'details_by_season':
                tvshow_details_by_season(self.params)
            elif action == 'resetposition':
                resetposition(self.params)
            elif action == 'toggleaddons':
                toggleaddons(self.params)
            elif action == 'playsfx':
                playsfx(self.params)
            elif action == 'playall':
                playall(self.params)
            elif action == 'playfolder':
                playfolder(self.params)
            elif action == 'playrandom':
                playrandom(self.params)
            elif action == 'playcinema':
                PlayCinema(self.params)
            elif action == 'blurimg':
                blurimg(self.params)
            elif action == 'txtfile':
                txtfile(self.params)
            elif action == 'fontchange':
                fontchange(self.params)
            elif action == 'split':
                split(self.params)
            elif action == 'setinfo':
                setinfo(self.params)
            elif action == 'lookforfile':
                lookforfile(self.params)
            elif action == 'restartservice':
                execute('NotifyAll(%s, restart)' % ADDON_ID)

if __name__ == "__main__":
    Main()

#!/usr/bin/python

########################

import sys
import xbmc
import xbmcplugin
import xbmcgui

from resources.lib.library import *
from resources.lib.helper import *

########################

class PluginActions(object):
    def __init__(self,params):
        self.params = params

    def folderjump(self):
        type = self.params.get('type')
        dbid = self.params.get('dbid')

        if type == 'tvshow':
            path = 'videodb://tvshows/titles/%s/' % dbid
        elif type == 'season':
            path = 'videodb://tvshows/titles/%s/%s/' % (dbid, self.params.get('season'))

        try:
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
        except Exception:
            pass

        go_to_path(path)

    def smsjump(self):
        letter = self.params.get('letter').upper()
        jumpcmd = None

        try:
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
        except Exception:
            pass

        if letter == '0':
            jumpcmd = 'lastpage' if xbmc.getInfoLabel('Container.SortOrder') == 'Descending' else 'firstpage'
        elif letter in ['A', 'B', 'C']:
            jumpcmd = 'jumpsms2'
        elif letter in ['D', 'E', 'F']:
            jumpcmd = 'jumpsms3'
        elif letter in ['G', 'H', 'I']:
            jumpcmd = 'jumpsms4'
        elif letter in ['J', 'K', 'L']:
            jumpcmd = 'jumpsms5'
        elif letter in ['M', 'N', 'O']:
            jumpcmd = 'jumpsms6'
        elif letter in ['P', 'Q', 'R', 'S']:
            jumpcmd = 'jumpsms7'
        elif letter in ['T', 'U', 'V']:
            jumpcmd = 'jumpsms8'
        elif letter in ['W', 'X', 'Y', 'Z']:
            jumpcmd = 'jumpsms9'

        if jumpcmd is not None:
            execute('SetFocus(50)')

            for i in range(40):
                json_call('Input.ExecuteAction',
                            params={'action': '%s' % jumpcmd}
                            )

                xbmc.sleep(50)

                if xbmc.getInfoLabel('ListItem.Sortletter').upper() == letter or letter == '0':
                    break
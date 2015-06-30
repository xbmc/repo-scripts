#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcplugin
import xbmcaddon
import socket
from traceback import print_exc

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()

        host = "localhost"
        port = int( __addon__.getSetting( "port" ) )

        try:
            clientsocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            clientsocket.connect( ( host, port ) )
            log( "(* -> %s) '%s'" %( host, self.TYPE ) )
            if self.ID is None:
                clientsocket.send( "%s||||%s||||EOD" %( self.TYPE, sys.argv[ 1 ] ) )
            else:
                clientsocket.send( "%s||||%s||||%s||||EOD" %( self.TYPE, self.ID, sys.argv[ 1 ] ) )
            message = clientsocket.recv( 128 ).split( "||||" )
            log( "(%s -> *) '%s' '%s'" %( host, message[ 0 ], message[ 1 ] ) )
            clientsocket.close()

        except:
            log( "(Widget) Unable to establish connection to service" )
            print_exc()
            xbmcplugin.endOfDirectory(handle= int(sys.argv[1]))

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
        except:
            params = {}
        self.TYPE = params.get( "?type", "" )
        self.ID = params.get( "id", None )

import xbmc
import xbmcaddon
import xbmcvfs
import inspect
import os
import sys
import socket
import re

class printDebug:

    def __init__(self, main, sub=None):

        self.main=main
        if sub:
            self.sub="."+sub
        else:
            self.sub=''

        self.level=settings.get_debug()

        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3
        self.token_regex=re.compile('-Token=[a-z|0-9].*[&|$]')
        self.ip_regex=re.compile('\.\d{1,3}\.\d{1,3}\.')        

        self.DEBUG_MAP={ self.DEBUG_OFF       : "off",
                         self.DEBUG_INFO      : "info",
                         self.DEBUG_DEBUG     : "debug",
                         self.DEBUG_DEBUGPLUS : "debug+"}

    def get_name(self, level):
        return self.DEBUG_MAP[level]

    def error(self,message):
        return self.__printDebug(message, 0)        

    def info(self, message):
        return self.__printDebug(message, 1)

    def debug(self, message):
        return self.__printDebug(message, 2)

    def dev(self, message):
        return self.__printDebug(message, 3)

    def debugplus(self, message):
        return self.__printDebug(message, 3)

    def __printDebug( self, msg, level=1 ):
        if self.level >= level :
            #msg=self.token_regex.sub("-Token=XXXXXXXXXX&", str(msg))
            #msg=self.ip_regex.sub(".X.X.", msg)
            print("%s%s -> %s : %s" % (self.main, self.sub, inspect.stack(0)[2][3], msg))
        return

    def __call__(self, msg, level=1):
        return self.__printDebug(msg, level)

def get_platform( ):
    if xbmc.getCondVisibility('system.platform.osx'):
        return "OSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return "ATV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux/RPi"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Linux/Android"
    return "Unknown"

def setup_python_locations():
    setup={}
    setup['__addon__'] = xbmcaddon.Addon()
    setup['__cachedir__'] = setup['__addon__'].getAddonInfo('profile')
    setup['__cwd__']     = xbmcvfs.translatePath(setup['__addon__'].getAddonInfo('path'))

    setup['__version__'] = setup['__addon__'].getAddonInfo('version')

    setup['__resources__'] = xbmcvfs.translatePath(os.path.join(setup['__cwd__'], 'resources', 'lib'))
    sys.path.append(setup['__resources__'])
    return setup                

GLOBAL_SETUP=setup_python_locations()
GLOBAL_SETUP['platform']=get_platform()
GENERIC_THUMBNAIL = "%s/resource/thumb.png" % GLOBAL_SETUP['__cwd__']
REQUIRED_REVISION="1.0.7"



# main import's 
import sys
import os
import xbmc
import xbmcaddon

# Script constants 
__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__      = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__language__     = __addon__.getLocalizedString

# Shared resources
BASE_RESOURCE_PATH = os.path.join(__cwd__, 'resources', 'lib')
sys.path.append (BASE_RESOURCE_PATH)

from utilities import *

log('script version %s started' % __addonversion__)

def culrc_run(mode):
    log('mode is %s' % mode)
    if not WIN.getProperty('culrc.running') == 'true':
        import gui
        gui.MAIN(mode=mode)
    elif not WIN.getProperty('culrc.guirunning') == 'TRUE':
        # we're already running, user clicked button on osd
        WIN.setProperty('culrc.force','TRUE')
    else:
        log('script already running')
        if __addon__.getSetting( "silent" ) == 'false':
            xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (__addonname__ , __language__(32158), 2000)).encode('utf-8', 'ignore'))

if ( __name__ == "__main__" ):
    service = __addon__.getSetting( "service" )
    # started as a service
    if sys.argv == ['']:
        if service == "true":
            culrc_run('service')
        else:
            log('service not enabled')
    # manually started
    else:
        if service == "true":
            culrc_run('service')
        else:
            culrc_run('manual')
xbmc.sleep(2000)
log('script version %s ended' % __addonversion__)

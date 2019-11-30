import sys
import os
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = xbmc.translatePath(ADDON.getAddonInfo('path')).decode('utf-8')
PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')
LANGUAGE = ADDON.getLocalizedString

BASE_RESOURCE_PATH = os.path.join(CWD, 'resources', 'lib')
sys.path.append(BASE_RESOURCE_PATH)

from utilities import *
from scrapertest import *
log('script version %s started' % ADDONVERSION)

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
        if ADDON.getSetting('silent') == 'false':
            dialog = xbmcgui.Dialog()
            dialog.notification(ADDONNAME, LANGUAGE(32158), time=2000, sound=False)

if (__name__ == '__main__'):
    service = ADDON.getSetting('service')
    # started as a service
    if sys.argv == ['']:
        if service == 'true':
            culrc_run('service')
        else:
            log('service not enabled')
    # manually started
    else:
        if len(sys.argv) == 2 and sys.argv[1] == 'test':
            test_scrapers()
        elif service == 'true':
            culrc_run('service')
        else:
            culrc_run('manual')

log('script version %s ended' % ADDONVERSION)

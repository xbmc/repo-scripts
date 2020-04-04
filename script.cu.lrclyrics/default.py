from lib.utils import *

log('script version %s started' % ADDONVERSION)
service = ADDON.getSettingBool('service')

if sys.argv == [''] and not service:
    log('service not enabled')
elif len(sys.argv) == 2 and sys.argv[1] == 'test':
    from lib.scrapertest import *
    test_scrapers()
elif not WIN.getProperty('culrc.running') == 'true':
    from lib import gui
    gui.MAIN(mode=service)
elif not WIN.getProperty('culrc.guirunning') == 'TRUE':
    WIN.setProperty('culrc.force','TRUE') # we're already running, user clicked button on osd
else:
    log('script already running')
    if not ADDON.getSettingBool('silent'):
        xbmcgui.Dialog().notification(ADDONNAME, LANGUAGE(32158), time=2000, sound=False)

log('script version %s ended' % ADDONVERSION)

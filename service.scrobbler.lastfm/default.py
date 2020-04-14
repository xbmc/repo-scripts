import sys
from lib.utils import *


if ( __name__ == "__main__" ):
    try:
        params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
    except:
        params = {}
    if params:
        # run as script
        from lib import love
        SESSION = 'love'
        log('script version %s started' % ADDONVERSION, SESSION)
        love.Love(params=params)
    else:
        # run as service
        from lib import lastfm
        SESSION = 'scrobbler'
        log('script version %s started' % ADDONVERSION, SESSION)
        lastfm.Main()
log('script stopped', SESSION)

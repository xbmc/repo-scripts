import xbmc
import xbmcaddon
import os, sys

_settings   = xbmcaddon.Addon()
_name       = _settings.getAddonInfo('name')

def log ( msg, log_level=xbmc.LOGNOTICE ):
    # URLref: http://farmdev.com/talks/unicode , http://stackoverflow.com/a/11339995/43774
    if isinstance( msg, basestring ):
        if not isinstance( msg, unicode ):
            # [str -> unicode] == msg.decode('utf-8')
            msg = unicode( msg, 'utf-8' )
    message = u'%s: %s' % (_name, msg)
    xbmc.log(msg=message.encode("utf-8"), level=log_level)

# -*- coding: utf-8 -*-
# Based on contents from https://github.com/Diecke/service.subtitles.addicted
# Thanks Diecke!

import xbmc

def log(module,msg):
  xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)

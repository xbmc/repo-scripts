# -*- coding: utf-8 -*-
import urllib
import urllib2
import socket
import sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import re
from datetime import datetime,timedelta
import time

import libmediathek3utils

def dialogDate():
	dialog = xbmcgui.Dialog()
	return dialog.numeric(1, libmediathek3utils.getTranslation(31030)).replace('/','').replace(' ','0')
	
def getSearchString():
	if libmediathek3utils.searchWorkaroundExists():
		d = libmediathek3utils.searchWorkaroundRead()
	else:
		dialog = xbmcgui.Dialog()
		d = dialog.input(libmediathek3utils.getTranslation(31039),type=xbmcgui.INPUT_ALPHANUM)
		libmediathek3utils.searchWorkaroundWrite(d)
	return urllib.quote_plus(d)

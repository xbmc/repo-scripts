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

from libmediathek3utils import getTranslation as translation

def dialogDate():
	dialog = xbmcgui.Dialog()
	return dialog.numeric(1, translation(31030)).replace('/','').replace(' ','0')
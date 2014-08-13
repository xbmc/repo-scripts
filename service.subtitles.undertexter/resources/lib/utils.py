# -*- coding: utf-8 -*-

import os
import sys
import urllib
import unicodedata
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import shutil

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__temp__       = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode('utf-8')

class URLOpener(urllib.FancyURLopener):
  version = 'User-Agent=XBMC Subtitle Addon'

def log(message):
  xbmc.log(('### %s' % message).encode('utf-8'), level=xbmc.LOGDEBUG)

def normalize_string(str):
  return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')    

def get_parameters():
  string     = sys.argv[2]
  parameters = {}

  if string.startswith('?'):
    string = string[1:]

  if string.endswith('/'):
    string = string[:-1]

  for pair in string.split('&'):
    if '=' in pair:
      key, value = pair.split('=')

      parameters[key] = urllib.unquote(value.decode('utf-8'))

  return parameters

def clean_temporary_directory():
  if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)

  xbmcvfs.mkdirs(__temp__)

def get_url(url):
  log('Getting content from URL: %s' % url)

  opener   = URLOpener()
  response = opener.open(url)
  content  = response.read()

  response.close()

  return content
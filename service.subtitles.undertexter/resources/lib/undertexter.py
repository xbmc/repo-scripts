# -*- coding: utf-8 -*-

import os
import utils
import urllib
import re
import HTMLParser
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

SUBTITLE_LANGUAGES = {
  'Swedish' : {
    'language_code' : 'sv',
    'search_url'    : 'http://undertexter.se/?p=soek&add=arkiv&str=%s',
    'regex_pattern' : '<tr>\s+<td .+?><a .+? href="(.+?)">\s+<img .+?></a>(?:[\s\S]+?<img .+?><br>\s+){2}(.+?)</td>\s+</tr>',
    'priority'      : 10
  },
  'English' : {
    'language_code' : 'en',
    'search_url'    : 'http://engsub.net/?p=eng_search&add=arkiv&str=%s',
    'regex_pattern' : '<tr>\s+<td .+?><a .+? href="(.+?)">\s+<img .+?></a>(?:[\s\S]+?<img .+?><br>\s+){2}(.+?)</td>\s+</tr>',
    'priority'      : 0
  }
}

SUBTITLE_EXTENSIONS = [
  '.srt', '.sub', '.txt', '.smi', '.ssa', '.ass'
]

def search(search_string, language):
  results     = []
  html_parser = HTMLParser.HTMLParser()

  if language in SUBTITLE_LANGUAGES:
    utils.log('Searching for %s subtitles: %s' % (language, search_string))

    # Language specific stuff
    language_code = SUBTITLE_LANGUAGES[language]['language_code']
    search_url    = SUBTITLE_LANGUAGES[language]['search_url']
    regex_pattern = SUBTITLE_LANGUAGES[language]['regex_pattern']
    priority      = SUBTITLE_LANGUAGES[language]['priority']

    # Get content
    content = utils.get_url(search_url % urllib.quote(search_string))

    # Parse results
    pattern = re.compile(regex_pattern)
    matches = pattern.finditer(content)

    # Loop through all matches
    for match in matches:
      results.append({
        'name'          : html_parser.unescape(match.group(2).decode('utf-8')),
        'language'      : language,
        'language_code' : language_code,
        'download_url'  : match.group(1),
        'priority'      : priority
      })
  else:
    utils.log('Unsupported language: %s' % language)

  return results

def download(url):
  subtitles = []

  # Clean temporary directory
  utils.clean_temporary_directory()

  # Get file from URL
  content = utils.get_url(url)

  if content:
    path = os.path.join(__temp__, 'subtitle.tmp')

    # Write content to local file
    utils.log('Writing to local file: %s' % path)

    with open(path, 'wb') as file_handle:
      file_handle.write(content)

    # Determine type of downloaded file
    utils.log('Opening temporary file for reading: %s' % path)

    with open(path, 'rb') as file_handle:
      file_handle.seek(0)

      # Get file header
      header = file_handle.read(4)

      # Archive or not?
      if header == 'Rar!':
        utils.log('Got archive (.rar)')

        path = os.path.join(__temp__, 'subtitle.rar')
      elif header[:2] == 'PK':
        utils.log('Got archive (.zip)')

        path = os.path.join(__temp__, 'subtitle.zip')
      else:
        utils.log('Unknown type (Assuming .srt)')

        path = os.path.join(__temp__, 'subtitle.srt')

    file_handle.close()

    # Rename file
    utils.log('Renaming file')

    os.rename(os.path.join(__temp__, 'subtitle.tmp'), path)

    # Extract if archive
    if os.path.splitext(path)[1] in ['.rar', '.zip']:
      utils.log('Extracting archive: %s' % path)

      #xbmc.sleep(500)
      xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (path, __temp__)).encode('utf-8'), True)

    # Get files with correct extension
    for subtitle in xbmcvfs.listdir(__temp__)[1]:
      if os.path.splitext(subtitle)[1] in SUBTITLE_EXTENSIONS:
        subtitles.append(os.path.join(__temp__, subtitle))

  return subtitles
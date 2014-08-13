# -*- coding: utf-8 -*-

import os
import sys
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode('utf-8')
__temp__       = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode('utf-8')

sys.path.append(__resource__)

import utils
import undertexter

def basic_search(search_string, languages):
  utils.log('Performing basic search: %s' % search_string)

  results = []

  for language in languages:
    try:
      results.extend(undertexter.search(search_string, language))
    except:
      utils.log('Search failed: %s (%s)' % (search_string, language))

  return results

def episode_search(tv_show, languages):
  utils.log('Performing episode search: %s s%se%s (%s)' % (tv_show['name'], tv_show['season'].zfill(2), tv_show['episode'].zfill(2), tv_show['title']))

  results       = []
  search_string = '%s s%se%s' % (tv_show['name'], tv_show['season'].zfill(2), tv_show['episode'].zfill(2))

  for language in languages:
    try:
      results.extend(undertexter.search(search_string, language))
    except:
      utils.log('Search failed: %s (%s)' % (search_string, language))

  return results

def download(url):
  utils.log('Downloading from URL: %s' % url)

  try:
    subtitles = undertexter.download(url)
  except:
    utils.log('Download failed: %s' % url)

  return subtitles

# Get parameters and decide what action to perform
parameters = utils.get_parameters()

if parameters['action'] in ['search', 'manualsearch']:
  # Set some variables
  search_string = parameters['searchstring'] if 'searchstring' in parameters else None
  tv_show       = utils.normalize_string(xbmc.getInfoLabel('VideoPlayer.TVshowtitle')) or None
  file_path     = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
  languages     = parameters['languages'].decode('utf-8').split(',')

  # If not manual search or a TV-show, use title as search string
  if not search_string and not tv_show:
    search_string = utils.normalize_string(xbmc.getInfoLabel('VideoPlayer.OriginalTitle') or xbmc.getInfoLabel('VideoPlayer.Title'))

  # Fix file paths
  if file_path.startswith('rar://'):
    file_path = os.path.dirname(file_path[6:])
  elif file_path.startswith('stack://'):
    paths = file_path.split(' , ')
    file_path = paths[0][8:]

  # Perform search
  results = []

  if tv_show:
    results = episode_search({
      'name'    : tv_show,
      'title'   : utils.normalize_string(xbmc.getInfoLabel('VideoPlayer.OriginalTitle') or xbmc.getInfoLabel('VideoPlayer.Title')),
      'season'  : xbmc.getInfoLabel('VideoPlayer.Season'),
      'episode' : xbmc.getInfoLabel('VideoPlayer.Episode')     
    }, languages)
  else:
    results = basic_search(search_string, languages)

  # Handle results
  if results:
    utils.log('Got %d results' % len(results))

    # Basic "sync" check
    dirname      = os.path.basename(os.path.dirname(file_path))
    filename_ext = os.path.basename(file_path)
    filename     = os.path.splitext(filename_ext)[0]

    names = [
      dirname,
      filename_ext,
      filename
    ]

    for result in results:
      for name in names:
        if name.lower() == result['name'].lower():
          result['sync'] = True

          break
        else:
          result['sync'] = False

    # Sort results by priority and sync
    results.sort(key=lambda x: (not x['sync'], not x['priority'], not x['name'][:1].isalpha(), x['name']))

    # Loop through all results and add to list
    for result in results:
      # Create list item
      list_item = xbmcgui.ListItem(
        label          = result['language'],
        label2         = result['name'],
        thumbnailImage = result['language_code']
      )

      # Generate URL
      url = 'plugin://%s/?action=download&url=%s' % (
        __scriptid__,
        urllib.quote(result['download_url'])
      )

      # Mark as synced?
      if result['sync']:
        list_item.setProperty('sync',  'true')

      # Add list item
      xbmcplugin.addDirectoryItem(
        handle   = int(sys.argv[1]),
        url      = url,
        listitem = list_item,
        isFolder = False
      )
elif parameters['action'] == 'download':
  # Download desired file
  subtitles = download(urllib.unquote(parameters['url']))

  # Add subtitle(s)
  for subtitle in subtitles:
    list_item = xbmcgui.ListItem(
      label = subtitle
    )

    xbmcplugin.addDirectoryItem(
      handle   = int(sys.argv[1]),
      url      = subtitle,
      listitem = list_item,
      isFolder = False
    )

# Send end of directory to XBMC
xbmcplugin.endOfDirectory(int(sys.argv[1]))
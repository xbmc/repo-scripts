# -*- coding: utf-8 -*-

import sys
import os
import urllib
import urllib2
import re
import HTMLParser
import shutil

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui

__addon__      = xbmcaddon.Addon()
#__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
#__scriptname__ = __addon__.getAddonInfo('name')
#__version__    = __addon__.getAddonInfo('version')
#__language__   = __addon__.getLocalizedString

#__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path'))
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile'))
#__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__       = xbmc.translatePath(os.path.join(__profile__, 'temp'))

#sys.path.append(__resource__)

HTTP_HEADERS = [
  ('User-Agent', 'XBMC Subtitle Add-on')
]

SUBTITLE_LANGUAGES = {
  'Swedish' : {
    'search_url'    : 'http://undertexter.se/?p=soek&add=arkiv&str=%s',
    'regex_pattern' : '<tr>\s+<td .+?><a .+? href="(.+?)">\s+<img .+?></a>(?:[\s\S]+?<img .+?><br>\s+){2}(.+?)</td>\s+</tr>',
    'priority'      : 10
  },
  'English' : {
    'search_url'    : 'http://engsub.net/?p=eng_search&add=arkiv&str=%s',
    'regex_pattern' : '<tr>\s+<td .+?><a .+? href="(.+?)">\s+<img .+?></a>(?:[\s\S]+?<img .+?><br>\s+){2}(.+?)</td>\s+</tr>',
    'priority'      : 0
  }
}

SUBTITLE_EXTENSIONS = [
  '.srt', '.sub', '.txt', '.smi', '.ssa', '.ass'
]

SEASONS = [
  '...?', 'First Season', 'Second Season', 'Third Season', 'Fourth Season', 'Fifth Season',
  'Sixth Season', 'Seventh Season', 'Eighth Season', 'Ninth Season', 'Tenth Season',
  'Eleventh Season', 'Twelfth Season', 'Thirteenth Season', 'Fourteenth Season', 'Fifteenth Season',
  'Sixteenth Season', 'Seventeenth Season', 'Eighteenth Season', 'Nineteenth Season', 'Twentieth Season',
  'Twenty-first Season', 'Twenty-second Season', 'Twenty-third Season', 'Twenty-fourth Season', 'Twenty-fifth Season',
  'Twenty-sixth Season', 'Twenty-seventh Season', 'Twenty-eighth Season', 'Twenty-ninth Season', 'Thirtieth Season'
]

ARCHIVE_EXTENSIONS = {
  '.rar' : 'Rar!',
  '.zip' : 'PK'
}

def log(message):
  xbmc.log('### %s' % message, level=xbmc.LOGDEBUG)

def get_parameters(string):
  parameters = {}

  # Remove leading question mark
  if string.startswith('?'):
    string = string[1:]

  # Remove trailing slash
  if string.endswith('/'):
    string = string[:-1]

  # Split and loop through all parameter pairs
  for pair in string.split('&'):
    if '=' in pair:
      key, value = pair.split('=')

      parameters[key] = urllib.unquote(value)

  return parameters

def get_content_from_url(url):
  log('Getting content from URL: %s' % url)

  response = urllib2.urlopen(url)
  content  = response.read()

  response.close()

  return content

def search_by_language(string, language):
  results     = []
  html_parser = HTMLParser.HTMLParser()

  if language in SUBTITLE_LANGUAGES:
    log('Searching for %s subtitles: %s' % (language, string))

    # Language specific stuff
    search_url    = SUBTITLE_LANGUAGES[language]['search_url']
    regex_pattern = SUBTITLE_LANGUAGES[language]['regex_pattern']
    priority      = SUBTITLE_LANGUAGES[language]['priority']

    # Get content
    content = get_content_from_url(search_url % urllib.quote(string))

    # Parse results
    pattern = re.compile(regex_pattern)
    matches = pattern.finditer(content)

    # Loop through all matches
    for match in matches:
      results.append({
        'name'          : html_parser.unescape(match.group(2)),
        'language'      : language,
        'language_code' : xbmc.convertLanguage(language, xbmc.ISO_639_1),
        'download_url'  : match.group(1),
        'priority'      : priority
      })
  else:
    log('Unsupported language: %s' % language)

  return results

def basic_search(string, languages):
  results = []

  for language in SUBTITLE_LANGUAGES:
    results.extend(search_by_language(string, language))

  return results

def movie_search(movie, languages):
  string  = movie['imdb'] or movie['title']
  results = []

  for language in SUBTITLE_LANGUAGES:
    results.extend(search_by_language(string, language))

  return results

def show_search(show, languages):
  string  = '%s s%se%s' % (show['name'], show['season'].zfill(2), show['episode'].zfill(2))
  results = []

  for language in SUBTITLE_LANGUAGES:
    # English subtitle searching works a little bit different when it comes to TV shows
    if language == 'English':
      season = int(show['season'])

      if season < len(SEASONS):
        temp_string  = '%s - %s' % (show['name'], SEASONS[season])
        temp_results = search_by_language(temp_string, language)

        # We want to ignore subtitles for other episodes
        match = [
          's%se%s' % (show['season'].zfill(2), show['episode'].zfill(2)),
          '%sx%s'  % (show['season'].zfill(2), show['episode'].zfill(2))
        ]

        for result in temp_results:
          if any(string_to_match in result['name'].lower() for string_to_match in match):
            results.append(result)
    else:
      results.extend(search_by_language(string, language))

  return results

def download(url):
  subtitles = []

  # Create/clean temporary directory
  if not os.path.exists(__profile__):
    os.mkdir(__profile__)

  if os.path.exists(__temp__):
    shutil.rmtree(__temp__)

  os.mkdir(__temp__)

  # Get file from URL
  content = get_content_from_url(url)

  if content:
    # Check if downloaded file is an archive
    for extension, header in ARCHIVE_EXTENSIONS.items():
      if content.startswith(header):
        log('Got archive (%s)' % extension)

        path = os.path.join(__temp__, 'subtitle%s' % extension)

    # Else assume it's a .srt file
    if not path:
      log('Got unknown type (Assuming .srt)')

      path = os.path.join(__temp__, 'subtitle.srt')

    # Write to local file
    with open(path, 'wb') as local_file:
      local_file.write(content)

    # Extract if archive
    if os.path.splitext(path)[1] in ARCHIVE_EXTENSIONS:
      log('Extracting archive: %s' % path)

      #xbmc.sleep(500)
      xbmc.executebuiltin('XBMC.Extract("%s","%s")' % (path, __temp__), True)

    # Get files with correct extension
    for current_path, folders, files in os.walk(__temp__):
      for file_ in files:
        if os.path.splitext(file_)[1] in SUBTITLE_EXTENSIONS:
          subtitles.append(os.path.join(current_path, file_))

  return subtitles

# Main program
if __name__ == '__main__':
  plugin_handle = int(sys.argv[1])
  parameters    = get_parameters(sys.argv[2])

  # Build and install custom urllib2 opener
  log('Installing custom urllib2 opener')

  opener            = urllib2.build_opener()
  opener.addheaders = HTTP_HEADERS

  urllib2.install_opener(opener)

  # Perform requested action
  log('Requested action: %s' % parameters['action'])

  if parameters['action'] in ['search', 'manualsearch']:
    search_string      = parameters['searchstring'] if 'searchstring' in parameters else None
    movie_title        = xbmc.getInfoLabel('VideoPlayer.OriginalTitle') or None
    show_title         = xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or None

    file_path          = urllib.unquote(xbmc.Player().getPlayingFile())
    languages          = parameters['languages'].split(',')
    preferred_language = parameters['preferredlanguage'] if 'preferredlanguage' in parameters else None

    # Fix file path
    if file_path.startswith('rar://'):
      file_path = os.path.dirname(file_path[6:])
    elif file_path.startswith('stack://'):
      paths = file_path.split(' , ')
      file_path = paths[0][8:]

    # Manual search
    if search_string:
      log('Performing manual search')

      results = basic_search(search_string, languages)
    # Movie search
    elif movie_title:
      log('Performing movie search')

      results = movie_search({
        'title' : movie_title,
        'year'  : xbmc.getInfoLabel('VideoPlayer.Year'),
        'imdb'  : xbmc.Player().getVideoInfoTag().getIMDBNumber() or None
      }, languages)
    # Show search
    elif show_title:
      log('Performing show search')

      results = show_search({
        'name'    : show_title,
        'title'   : xbmc.getInfoLabel('VideoPlayer.Title'),
        'season'  : xbmc.getInfoLabel('VideoPlayer.Season'),
        'episode' : xbmc.getInfoLabel('VideoPlayer.Episode') 
      }, languages)
    # Filename search
    else:
      log('Performing filename search')

      # Remove extension from filename
      filename = os.path.splitext(xbmc.getInfoLabel('VideoPlayer.Title'))[0]
      results  = basic_search(filename, languages)

    # Handle results
    if results:
      log('Got %d results' % len(results))

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
      results.sort(key=lambda x: (not x['sync'], not x['language'] == preferred_language, not x['priority'], not x['name'][:1].isalpha(), x['name']))

      # Loop through all results
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
          handle   = plugin_handle,
          url      = url,
          listitem = list_item
        )
    else:
      log('No results')
  elif parameters['action'] == 'download':
    log('Downloading subtitle from URL: %s' % parameters['url'])

    # Download desired file
    subtitles = download(parameters['url'])

    # Add subtitle(s)
    if subtitles:
      for subtitle in subtitles:
        list_item = xbmcgui.ListItem(
          label = subtitle
        )

        xbmcplugin.addDirectoryItem(
          handle   = plugin_handle,
          url      = subtitle,
          listitem = list_item
        )

  # Send end of directory to XBMC
  xbmcplugin.endOfDirectory(
    handle = plugin_handle
  )
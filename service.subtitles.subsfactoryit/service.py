# -*- coding: utf-8 -*- 

import os
import re
import sys
import xbmc
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
from bs4 import BeautifulSoup

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

sys.path.append (__resource__)

# Release list (name on site, name for display)
release_list = [
['normale', 'Normale'],
['720p', '720p'],
['web', 'WEB-DL'],
['bluray', 'BluRay'],
['dvdrip', 'DVDRip'],
['bdrip', 'BDRip']]
# Revison list
revision_list = [
['proper', 'Proper'],
['fixed', 'Fixed'],
['resynched', 'Resynched'],
['v2', 'V2']]
# Exeption_list (xbmc possible name, site name)
exeption_list = [
['Marvel\'s Agents of S.H.I.E.L.D.', 'Agents of SHIELD'],
['Dr. House Medical Division', 'House'],
['24: Live Another Day', '24'],
['Law & Order: UK', 'Law and Order UK'],
['Mr Selfridge', 'Mr. Selfridge'],
['Survivors (2008)', 'Survivors 2008'],
['V (2009)', 'V 2009']]

allowed_exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']

def log(module, msg):
  xbmc.log((u'### [' + module + u'] - ' + msg).encode('utf-8'), level = xbmc.LOGDEBUG)

def geturl(url, post):
  log( __scriptname__ , 'Getting url: %s Post: %s' % (url, post))
  try:
    headers = { 'User-Agent' : 'XBMC Subsfactory Subtitle downloader' }
    req = urllib2.Request(url, post, headers)
    content = urllib2.urlopen(req).read()
  except:
    log( __scriptname__ , "Failed to get url:%s" % (url))
    content = None
  return(content)

def checkSync(fn, release):
  fn = fn.lower()
  check = False
  if release == 'WEB-DL':           
    if ('web-dl' in fn) or ('web.dl' in fn) or ('webdl' in fn) or ('web dl' in fn):
      check = True
  elif release == '720p':           
    if ('720p' in fn) and ('hdtv' in fn):
      check = True
  elif release == 'Normale':
    if ('hdtv' in fn) and ( not ('720p' in fn)):
      check = True
  elif release == 'BluRay':
    if ('bluray' in fn):
      check = True
  elif release == 'BDRip':
    if ('bdrip' in fn):
      check = True
  elif release == 'DVDRip':
    if ('dvdrip' in fn):
      check = True
  return(check)

def Search(item):
  if 'ita' in item['3let_language']:
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    log(__scriptname__, "search='%s', filename='%s', addon_version=%s" % (item, filename, __version__))

    if item['title'] and item['year']:
      xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32002))).encode('utf-8'))
      log(__scriptname__, 'SubsFactory only works with tv shows. Skipped')
    else:
      req_data = {}
      item_proc = {}
      check = True
      name = None

      if item['mansearch']:
        name = re.sub(r'(%20)', ' ', item['mansearchstr'])
      else:
        # Check if the serie name is an exeption
        for exeption in exeption_list:
          if item['tvshow'] == exeption[0]:
            name = exeption[1]
        if name is None:
          # Prepare name without year and country
          name = re.sub(r'(( ((\(\d\d\d\d\))|((\([a-zA-Z]{2,3})\))))|(((\(\d\d\d\d\))|((\([a-zA-Z]{2,3})\)))))*$', '', item['tvshow'])

      # Remove special chars
      name = re.sub(r'[^\w\s]', '', name)
      # Change spaces in dots
      dotted_name = re.sub(r'\s+', '.', name)
      # Prepare season number in format XX
      if len(item['season']) < 2:
        item_proc['season'] = '0' + item['season']
      else:
        item_proc['season'] = item['season']
      # Prepare episode number in format XX
      if len(item['episode']) < 2:
        item_proc['episode'] = '0' + item['episode']
      else:
        item_proc['episode'] = item['episode']

      #log( __scriptname__ , item['season'])

      # Prepare the request
      url = 'http://subsfactory.it/subtitle/search.php?'

      if item['mansearch']:
        req_strings = [
        [dotted_name, True, None],
        [name, True, None]]
      else:
        # Search strings, is a packed season string
        req_strings = [
        [dotted_name + '.s' + item_proc['season'] + 'e' + item_proc['episode'], False, None],
        [dotted_name + '.s' + item_proc['season'] + '.', True, None],
        [dotted_name, True, 'stagione ' + item['season']],
        [name, True, 'stagione ' + item['season']],
        [re.sub(r"\s+", '', re.sub(r'[^\w\s]', '', name)), True, 'stagione ' + item['season']]]

      for req_string in req_strings:
        if check:
          # Prepare post
          req_data = urllib.urlencode({'q' : req_string[0], 'action' : 'showsearchresults_byfilename', 'loc' : 'files/'})
          # Do the request
          page = geturl(url, req_data)
          # Remove all img tags to avoid html parser errors and parse
          page = BeautifulSoup(re.sub(r'<(\s*)img[^<>]*>', '', page))

          subs = page.find('div').findAll('table')[4].findAll('tr', attrs={'valign' : 'top'})
          if subs is not None:
            for sub in subs:
              # Get subtitle url
              sub_url = sub.find('td', attrs={'align' : 'center' }).find('a')['href']
              # Get release
              sub_releases = sub.find('td', attrs={'align' : 'left' }).findAll('font')[1].get_text()
              # Get name if manual search
              if item['mansearch']:
                subs_title = sub.find('td', attrs={'align' : 'left' }).findAll('font')[0].find('a').get_text()
                # Remove .zip, .srt, .sub, .ita, it and .subsfactory
                subs_title = re.sub(r'(\.sub[a-zA-Z]*)|(\.zip)|(\.srt)(?!\w)|(\.ita)(?!\w)|(\.it)(?!\w)', '', subs_title)
                # Remove quality
                for release in release_list:
                  subs_title = re.sub(r'\.' + release[0] + '(?!\w)', '', subs_title)
                # Change dots in spaces
                subs_title = re.sub(r'(\.)', ' ', subs_title)

              # Compare the releases and send to xbmc
              release_names = []
              goodSeason = True
              if req_string[2] is None:
                for release in release_list:
                  if re.search(release[0], sub_releases, re.IGNORECASE | re.DOTALL):
                    release_names.append(release[1])
              elif re.search(req_string[2], sub_releases, re.IGNORECASE | re.DOTALL):
                for release in release_list:
                  if re.search(release[0], sub_releases, re.IGNORECASE | re.DOTALL):
                    release_names.append(release[1])
              else:
                goodSeason = False
              if not release_names:
                release_names.append('Normale')

              # Check if is a revision
              for revision in revision_list:
                if re.search(revision[0], sub_releases, re.IGNORECASE | re.DOTALL):
                  revision_name = ' ' + revision[1]
                else:
                  revision_name = ''

              check = False

              # Add to xbmc
              if goodSeason:
                if not item['mansearch']:
                  subs_title = name + ' ' + item['season'] + 'x' + item['episode']
                for release_name in release_names:
                  listitem = xbmcgui.ListItem(label = 'Italian',
                                              label2 = subs_title[0].upper() + subs_title[1:] + ' ' + release_name + revision_name,
                                              thumbnailImage = 'it'
                                              )
                  # Check sync
                  if not item['mansearch']:
                    if checkSync(os.path.splitext(os.path.basename(item['file_original_path']))[0], release_name):
                      listitem.setProperty( "sync",        '{0}'.format("true").lower() )  # set to "true" if subtitle is matched by hash

                  ## below arguments are optional, it can be used to pass any info needed in download function
                  ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
                  if req_string[1]:
                    xbmc_url = "plugin://%s/?action=download&url=%s&multi=%s&season=%s&episode=%s" % (__scriptid__, sub_url, '1', item['season'], item['episode'])
                  else:
                    xbmc_url = "plugin://%s/?action=download&url=%s&multi=%s" % (__scriptid__, sub_url, '0')

                  ## add it to list, this can be done as many times as needed for all subtitles found
                  xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=xbmc_url,listitem=listitem,isFolder=False)
  else:
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32001))).encode('utf-8'))
    log(__scriptname__, 'SubsFactory only works with italian. Skipped')

def getFolders(directory):
  folders = []
  for file in os.listdir(directory):
    if os.path.isdir(os.path.join(directory, file)):
      folders.append(os.path.join(directory, file))
  return folders

def searchEpisode(season, episode):
  # Prepare season number in format XX
  if len(season) < 2:
    season_proc = '0' + season
  else:
    season_proc = season
  # Prepare episode number in format XX
  if len(episode) < 2:
    episode_proc = '0' + episode
  else:
    episode_proc = episode

  # All the posibilities to identify the episode from straight to less straight
  search_strings = [
  's' + season_proc + 'e' + episode_proc,
  's' + season + 'e' + episode,
  season + 'x' + episode,
  's.' + season_proc + 'e.' + episode_proc,
  's.' + season + 'e.' + episode,
  season + '.x.' + episode,
  season_proc + '.' + episode_proc,
  season + '.' + episode,
  season_proc + episode_proc,
  season + episode,
  episode_proc,
  episode]

  check = True
  episode_file = None
  folders = [__temp__]

  for folder in folders:
    # Get the folder list in the folder
    newFolders = getFolders(folder)
    for newFolder in newFolders:
      folders.append(newFolder)
    for search_string in search_strings:
      if check:
        # Search the episode number string
        for file in os.listdir(folder):
          if os.path.splitext(file)[1] in allowed_exts:
            if search_string in file.lower():
              episode_file = os.path.join(folder, file)
              check = False

  return episode_file

def Download(file_name, file_directory, season, episode):
  subtitle_list = []
  ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
  ## pass that to XBMC to copy and activate
  if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
  xbmcvfs.mkdirs(__temp__)

  file_data = geturl('http://subsfactory.it/subtitle/index.php?action=downloadfile&filename=' + file_name + '&directory=' + file_directory +'&', None)
  subs_files = []

  # Check if subtitle is downloaded
  if file_data:
    # Save file to the temp folder
    local_file_handle = open(os.path.join(__temp__, 'subsfactory.tmp'), 'wb')
    local_file_handle.write(file_data)
    local_file_handle.close()

    #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
    tmp_file = open(os.path.join(__temp__, 'subsfactory.tmp'), 'rb')
    tmp_file.seek(0)
    if tmp_file.read(1) == 'R':
      ext = 'rar'
      packed = True
    else:
      tmp_file.seek(0)
      if tmp_file.read(1) == 'P':
        ext = 'zip'
        packed = True
      else:
        ext = 'srt'
        packed = False
    tmp_file.close()
    # Rename file with the good ext
    os.rename(os.path.join(__temp__, 'subsfactory.tmp'), os.path.join(__temp__, 'subsfactory.' + ext))

    if packed:
      # Extract subs
      xbmc.sleep(500)
      xbmc.executebuiltin(('XBMC.Extract(' + os.path.join(__temp__, 'subsfactory.' + ext) + ',' + __temp__ +')').encode('utf-8'), True)

      if season is not None:
        episode_file = searchEpisode(season, episode)
        if episode_file is not None:
          subs_files.append(episode_file)
      else:
        folders = [__temp__]

        for folder in folders:
          newFolders = getFolders(folder)
          for newFolder in newFolders:
            folders.append(newFolder)
          for file in os.listdir(folder):
            if os.path.splitext(file)[1] in allowed_exts:
              subs_files.append(os.path.join(folder, file))
    else:
      subs_files.append(os.path.join(__temp__, 'subsfactory.' + ext))

  # Send the subtitle list to xbmc
  return subs_files
 
def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')    
 
def get_params():
  param=[]
  paramstring=sys.argv[2]
  if len(paramstring)>=2:
    params=paramstring
    cleanedparams=params.replace('?','')
    if (params[len(params)-1]=='/'):
      params=params[0:len(params)-2]
    pairsofparams=cleanedparams.split('&')
    param={}
    for i in range(len(pairsofparams)):
      splitparams={}
      splitparams=pairsofparams[i].split('=')
      if (len(splitparams))==2:
        param[splitparams[0]]=splitparams[1]
                                
  return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
  item = {}
  item['temp']               = False
  item['rar']                = False
  item['mansearch']          = False
  item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
  item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
  item['3let_language']      = []
  
  if 'searchstring' in params:
    item['mansearch'] = True
    item['mansearchstr'] = params['searchstring']

  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
  
  if item['title'] == "":
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
    
  if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
    item['season'] = "0"                                                          #
    item['episode'] = item['episode'][-1:]
  
  if ( item['file_original_path'].find("http") > -1 ):
    item['temp'] = True

  elif ( item['file_original_path'].find("rar://") > -1 ):
    item['rar']  = True
    item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

  elif ( item['file_original_path'].find("stack://") > -1 ):
    stackPath = item['file_original_path'].split(" , ")
    item['file_original_path'] = stackPath[0][8:]
  
  Search(item)  

elif params['action'] == 'download':
  if params['multi'] == '1':
    season = params['season']
    episode = params['episode']
  else:
    season = None
    episode = None
  ## we pickup all our arguments sent from def Search()
  subs = Download(params['filename'], params['directory'], season, episode)
  ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
  
  
xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC
  
  
  
  
  
  
  
  
  
    

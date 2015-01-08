# -*- coding: utf-8 -*- 

import os
import sys
import time
import glob
import shutil
import urllib
import codecs

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin

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

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append (__resource__)

from SubtitleHelper import log, build_search_string, normalizeString
from TorecSubtitlesDownloader import TorecSubtitlesDownloader
    
def convert_to_utf(file):
  ''' 
  Convert a file in cp1255 encoding to utf-8
  :param file: file to converted from CP1255 to UTF8
  '''
  try:
    with codecs.open(file,"r","cp1255") as f:
      srtData = f.read()

    with codecs.open(file, 'w', 'utf-8') as output:
      output.write(srtData)
  except UnicodeDecodeError:
    log(__name__, "got unicode decode error with reading subtitle data")

def search(item):
    best_match_id = None
    downloader    = TorecSubtitlesDownloader()
    search_data   = None
    
    start_time = time.time()

    try:
        search_start_time = time.time()
        search_string     = build_search_string(item)
        search_data       = downloader.search(search_string)
        
        log(__name__, "search took %f" % (time.time() - search_start_time))
    except:
        log( __name__, "failed to connect to service for subtitle search")
        xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32001))).encode('utf-8'))
        return
    
    list_items = []
    if search_data:
      best_match_id = downloader.get_best_match_id(os.path.basename(item['file_original_path']), search_data)

      for item_data in search_data.options:
          listitem = xbmcgui.ListItem(label    = "Hebrew",
                                label2         = item_data.name,
                                iconImage      = "0",
                                thumbnailImage = "he",
                                )
                                

          url = "plugin://%s/?action=download&page_id=%s&subtitle_id=%s&filename=%s" % (__scriptid__,
                                                                      search_data.id,
                                                                      item_data.id,
                                                                      item_data.name
                                                                      )

          if best_match_id != None and item_data.id == best_match_id:
            log(__name__, "Found most relevant option to be : %s" % item_data.name)
            listitem.setProperty("sync", "true")
            list_items.insert(0, (url, listitem, False,))
          else:
            list_items.append((url, listitem, False,))
    
    xbmcplugin.addDirectoryItems(handle=int(sys.argv[1]), items=list_items)
    log(__name__, "Overall search took %f" % (time.time() - start_time))

def download(page_id, subtitle_id,filename, stack=False):
    files = glob.glob(os.path.join(__temp__, "*.srt"))
    for f in files:
      log(__name__, "deleting %s" % f)
      os.remove(f)

    subtitle_list = []
    exts = [".srt", ".sub"]
    
    delay         = 20
    download_wait = delay
    downloader    = TorecSubtitlesDownloader()
    start_time    = time.time()

    try:
        # Wait the minimal time needed for retrieving the download link
        for i in range (int(download_wait)):
            result =  downloader.getDownloadLink(page_id, subtitle_id, False)
            if (result != None):
                break
            log(__name__ ,"download will start in %i seconds" % (delay,))
            delay -= 1
            time.sleep(1)
    except:
        log( __name__, "failed to connect to service for subtitle download")
        return subtitle_list
        
    if result != None:
        log(__name__ ,"Downloading subtitles from '%s'" % result)
        
        (subtitleData, subtitleName) = downloader.download(result)
        zip = os.path.join(__temp__, "Torec.zip")
        with open(zip, "wb") as subFile:
            subFile.write(subtitleData)

        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip,__temp__,)).encode('utf-8'), True)

        for file in xbmcvfs.listdir(__temp__)[1]:
            log(__name__, "file=%s" % file)
            file = os.path.join(__temp__, file)
            if (os.path.splitext(file)[1] in exts):
              convert_to_utf(file)
              subtitle_list.append(file)
      
    log(__name__, "Overall download took %f" % (time.time() - start_time))
    return subtitle_list
    
    
def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string 
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
  
  log( __name__, "action '%s' called" % params['action'])
  item = {}
  item['temp']               = False
  item['rar']                = False
  item['mansearch']          = False
  item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
  item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
  item['3let_language']      = []
  
  if 'searchstring' in params:
    item['mansearch'] = True
    item['mansearchstr'] = params['searchstring']     
  
  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
  
  if item['title'] == "":
    log( __name__, "VideoPlayer.OriginalTitle not found")
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
  
  log(__scriptname__, "%s" % item)
  
  search(item)  

elif params['action'] == 'download':
  subs = download(params["page_id"],params["subtitle_id"],params["filename"])
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)
  
  
xbmcplugin.endOfDirectory(int(sys.argv[1]))


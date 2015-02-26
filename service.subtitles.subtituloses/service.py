# -*- coding: utf-8 -*- 

"""
This addon is a modification of quillo86's addon for XBMC Frodo, adapted to Gotham using
manacker's service.subtitles.subscene as base code

Original code by quillo86 (https://github.com/quillo86) and manacker (https://github.com/manacker)
Adaptation by infinito (https://github.com/infinicode)
"""

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import shutil
import unicodedata
import urllib2

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

from SubEsUtilities import search_tvshow, log



""" Called when searching for subtitles from XBMC """
def Search(item):
	subs = search_tvshow(item['tvshow'], item['season'], item['episode'], item['2let_language'], item['file_original_path'])
	for sub in subs:
		append_subtitle(sub)

def append_subtitle(item):
    listitem = xbmcgui.ListItem(label=item['language_name'],  label2=item['filename'], iconImage=item['rating'], thumbnailImage=item['lang'])

    listitem.setProperty("sync",  'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp", 'true' if item["hearing_imp"] else 'false')

    ## below arguments are optional, it can be used to pass any info needed in download function
    ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
    url = "plugin://%s/?action=download&link=%s&filename=%s" % (__scriptid__, item['link'], item['filename'])

    ## add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

""" Called when subtitle download request from XBMC """
def Download(link, filename):
    subtitle_list = []
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]

    if link:
        downloadlink = link
        log(__name__, "Downloadlink %s" % link)

        class MyOpener(urllib.FancyURLopener):
            version = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"

        my_urlopener = MyOpener()
        my_urlopener.addheader('Referer', link)
        postparams = None
        
        
        log(__name__, "Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (link, link, postparams))
        response = my_urlopener.open(link, postparams)
        local_tmp_file = os.path.join(__temp__, "sub.srt")
        
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)
        try:
            log(__name__, "Saving subtitles to '%s'" % local_tmp_file)
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(response.read())
            local_file_handle.close()
            
            subtitle_list.append(local_tmp_file)
            log(__name__, "=== returning subtitle file %s" % file)

        except:
            log(__name__, "Failed to save subtitle to %s" % local_tmp_file)

    return subtitle_list

""" Get parameters from XBMC and launch actions """
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

if params['action'] == 'search':
  item = {}
  item['temp']               = False
  item['rar']                = False
  item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
  item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
  item['3let_language']      = []
  item['2let_language']      = []
  
  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
    item['2let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_1))
  
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

  # required if tvshow is not indexed/recognized in library
  if item['tvshow'] == "":  
    log(__name__, "item %s" % item)
    # replace dots with spaces in title
    titulo = re.sub(r'\.', ' ', item['title'])
    log(__name__, "title no dots: %s" % titulo)
    mo = re.search(r'(.*)[sS](\d+)[eE](\d+)', titulo) #S01E02 like
    if not mo:
      mo = re.search(r'(.*)(\d\d)[xX](\d+)', titulo) # old 10x02 style
    if not mo:
      mo = re.search(r'(.*)(\d)[xX](\d+)', titulo) # old 1x02 style
    if not mo:
      mo = re.search(r'(.*) (\d+)(\d\d)', titulo) # 102 style 
    # split title in tvshow, season and episode
    if mo:
      item['tvshow'] = mo.group(1)
      item['season'] = mo.group(2)
      item['episode'] = mo.group(3)
      log(__name__, "item %s" % item)
    else:
      log(__name__, "could not parse tvshow name and episode number")
  
  Search(item)  

elif params['action'] == 'download':
  ## we pickup all our arguments sent from def Search()
  subs = Download(params["link"],params["filename"])
  ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
  
  
xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC
  
  
  
  
  
  
  
  
  
    

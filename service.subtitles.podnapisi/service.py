# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import urllib,urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin,shutil
from zipfile import ZipFile
from cStringIO import StringIO
import uuid

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

from pn_utilities import OSDBServer, log, hashFile, normalizeString, languageTranslate

def Search( item ):
  osdb_server = OSDBServer()
  osdb_server.create()    
  subtitles_list = []
  
  if item['temp'] : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      file_size, SubHash = hashFile(item['file_original_path'], item['temp'])
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  if hash_search :
    log( __name__ ,"Search for [%s] by hash" % (os.path.basename( item['file_original_path'] ),))
    subtitles_list = osdb_server.searchsubtitles_pod( SubHash ,item['3let_language'], False)
  if not subtitles_list:
    log( __name__ ,"Search for [%s] by name" % (os.path.basename( item['file_original_path'] ),))
    subtitles_list = osdb_server.searchsubtitlesbyname_pod(item['title'],
                                                           item['tvshow'],
                                                           item['season'],
                                                           item['episode'],
                                                           item['3let_language'],
                                                           item['year'],
                                                           False )

  if subtitles_list:
    for it in subtitles_list:
      listitem = xbmcgui.ListItem(label=it["language_name"],
                                  label2=it["filename"],
                                  iconImage=it["rating"],
                                  thumbnailImage=it["language_flag"]
                                  )

      listitem.setProperty( "sync", ("false", "true")[it["sync"]] )
      listitem.setProperty( "hearing_imp", ("false", "true")[it["hearing_imp"]] )
      
      url = "plugin://%s/?action=download&link=%s&filename=%s" % (__scriptid__,
                                                                  it["link"],
                                                                  it["filename"]
                                                                  )
      
      xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)


def Download(url,filename):
  if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
  xbmcvfs.mkdirs(__temp__) 
  subtitle_list = []

  try:
    log( __name__ ,"Extract using 'ZipFile' method")
    response = urllib2.urlopen(url)
    raw = response.read()      
    archive = ZipFile(StringIO(raw), 'r')
    files = archive.namelist()
    files.sort()
    index = 1
    
    for file in files:
      contents = archive.read(file)
      extension = file[file.rfind('.') + 1:]

      if len(files) == 1:
        dest = os.path.join(__temp__, "%s.%s" %(str(uuid.uuid4()), extension))
      else:
        dest = os.path.join(__temp__, "%s.%d.%s" %(str(uuid.uuid4()), index, extension))
      
      f = open(dest, 'wb')
      f.write(contents)
      f.close()
      subtitle_list.append(dest)
      index += 1
  except:
    log( __name__ ,"Extract using 'XBMC.Extract' method")
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
    zip = os.path.join( __temp__, "PN.zip")
    f = urllib.urlopen(url)
    with open(zip, "wb") as subFile:
      subFile.write(f.read())
    subFile.close()
    xbmc.sleep(500)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip,__temp__,)).encode('utf-8'), True)
    for subfile in xbmcvfs.listdir(zip)[1]:
      file = os.path.join(__temp__, subfile.decode('utf-8'))
      if (os.path.splitext( file )[1] in exts):
        subtitle_list.append(file)

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

if params['action'] == 'search':
  log( __name__, "action 'search' called")
  item = {}
  item['temp']               = False
  item['rar']                = False
  item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
  item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
  item['3let_language']      = [] #['scc','eng']
  
  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(languageTranslate(lang,0,1))
  
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
  
  Search(item)  

elif params['action'] == 'download':

  osdb_server = OSDBServer()
  url = osdb_server.download("", params["link"])
  if url:
    subs = Download(url,params["filename"])
    for sub in subs:
      listitem = xbmcgui.ListItem(label=sub)
      xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
  
elif params['action'] == 'manualsearch':
  xbmc.executebuiltin(u'Notification(%s,%s,2000,%s)' %(__scriptname__,
                                                       __language__(32004),
                                                       os.path.join(__cwd__,"icon.png")
                                                      )
                      )
  
xbmcplugin.endOfDirectory(int(sys.argv[1]))
  
  
  
  
  
  
  
  
  
    

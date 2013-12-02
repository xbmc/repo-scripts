# -*- coding: utf-8 -*- 

import os
import re
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata

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


BASE_URL = "http://www.subscenter.org"

#===============================================================================
# Regular expression patterns
#===============================================================================
MULTI_RESULTS_PAGE_PATTERN = u"עמוד (?P<curr_page>\d*) \( סך הכל: (?P<total_pages>\d*) \)"
SEARCH_RESULTS_PATTERN = "<div class=\"generalWindowRight\">.*?<a href=\"(?P<sid>.*?)\">"

#===============================================================================
# Private utility functions
#===============================================================================
def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):
    # Fix URLs with spaces in them
    url = url.replace(" ","%20")
    content = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        response = urllib.urlopen(url)
        content = response.read()
    except Exception as e:
        log( __name__ ,"Failed to get url: %s\n%s" % (url, e))
    # Second parameter is the filename
    return content

def getURLfilename(url):
    # Fix URLs with spaces in them
    url = url.replace(" ","%20")
    filename = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        response = urllib.urlopen(url)
        filename = response.headers['Content-Disposition']
        filename = filename[filename.index("filename="):]
    except Exception as e:
        log( __name__ ,"Failed to get url: %s\n%s" % (url, e))
    # Second parameter is the filename
    return filename

# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(subtitlePageID,languageList):

    subtitlesList = []
    # Retrieve the subtitles page (html)
    try:
        subtitlePage = getURL(BASE_URL + subtitlePageID)
    except:
        # Didn't find the page - no such episode?
        return
    # Didn't find the page - no such episode?
    if (not subtitlePage):
        return
    # Find subtitles dictionary declaration on page
    tempStart = subtitlePage.index("subtitles_groups = ")
    # Look for the following line break
    tempEnd = subtitlePage.index("\n",subtitlePage.index("subtitles_groups = "))
    toExec = "foundSubtitles = "+subtitlePage[tempStart+len("subtitles_groups = "):tempEnd]
    # Remove junk at the end of the line
    toExec = toExec[:toExec.rfind("}")+1]
    # Replace "null" with "None"
    toExec = toExec.replace("null","None")
    exec(toExec)
    for language in foundSubtitles.keys():
      if (xbmc.convertLanguage(language,xbmc.ISO_639_2) in languageList): 
          for translator in foundSubtitles[language]:
              for quality in foundSubtitles[language][translator]:
                  for rating in foundSubtitles[language][translator][quality]:
                    subtitlesList.append({'lang_index' : languageList.index(xbmc.convertLanguage(language,xbmc.ISO_639_2)),
                                          'filename' : foundSubtitles[language][translator][quality][rating]["subtitle_version"],
                                          'link' : foundSubtitles[language][translator][quality][rating]["key"],
                                          'language_name' : xbmc.convertLanguage(language,xbmc.ENGLISH_NAME),
                                          'language_flag' : language,
                                          'ID': foundSubtitles[language][translator][quality][rating]["id"],
                                          'rating' : rating,
                                          'sync' : foundSubtitles[language][translator][quality][rating]["is_sync"],
                                          'hearing_imp' : foundSubtitles[language][translator][quality][rating]["hearing_impaired"],
                                          })
    return subtitlesList


def Search(item):

  if item['tvshow']:
    searchString = item['tvshow'].replace(" ","+")
  else:
    searchString = item['title'].replace(" ","+")
  log( __name__ ,"Search string = %s" % (searchString.lower()))
  
  # Retrieve the search results (html)
  searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
  # Search most likely timed out, no results
  if (not searchResults):
      return

  # Look for subtitles page links
  subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
  # Look for more subtitle pages
  pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
  # If we found them look inside for subtitles page links
  if (pages):
      while (not (int(pages.group("curr_page"))) == int(pages.group("total_pages"))):
          searchResults = getURL(BASE_URL + "/he/subtitle/search/?q="+searchString.lower()+"&page="+str(int(pages.group("curr_page"))+1))
          tempSIDs = re.findall(SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
          for sid in tempSIDs:
              subtitleIDs.append(sid)
          pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
  # Uniqify the list
  subtitleIDs=list(set(subtitleIDs))
  # If looking for tvshos try to append season and episode to url
  if item['tvshow']:
      for i in range(len(subtitleIDs)):
          if (subtitleIDs[i].find("series") > 0):
              subtitleIDs[i] += "/"+season+"/"+episode+"/"

  for sid in subtitleIDs:
      subtitles_list = getAllSubtitles(sid, item['3let_language'])
      if subtitles_list:
        for it in subtitles_list:
          listitem = xbmcgui.ListItem(label=it["language_name"],
                                      label2=it["filename"],
                                      iconImage=it["rating"],
                                      thumbnailImage=it["language_flag"]
                                      )
          if it["sync"]:
            listitem.setProperty( "sync", "true" )
          else:
            listitem.setProperty( "sync", "false" )
            
          if it.get("hearing_imp", False):
            listitem.setProperty( "hearing_imp", "true" )
          else:
            listitem.setProperty( "hearing_imp", "false" )
      
        url = "plugin://%s/?action=download&link=%s&ID=%s&filename=%s" % (__scriptid__, it["link"], it["ID"],it["filename"])      
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
   


def Download(id,key,filename, stack=False):
  subtitle_list = []
  ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
  ## pass that to XBMC to copy and activate
  if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
  xbmcvfs.mkdirs(__temp__)

  url = BASE_URL + "/subtitle/download/he/" + str(id)+"/?v="+filename+"&key="+key
  log( __name__ ,"Fetching subtitles using url %s" % (url))
  # Get the intended filename (don't know if it's zip or rar)
  archive_name = getURLfilename(url)
  # Get the file content using geturl()
  content = getURL(url)
  subs_file = ""
  if content:
    local_tmp_file = os.path.join(__temp__, archive_name)
    log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
    try:
      local_file_handle = open(local_tmp_file, "wb")
      local_file_handle.write(content)
      local_file_handle.close()
      xbmc.sleep(500)
    except:
      log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))

  # Extract the zip file and find the new sub/srt file
  xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (local_tmp_file,__temp__,)).encode('utf-8'), True)
  for file in xbmcvfs.listdir(__temp__)[1]:
    full_path = os.path.join(__temp__, file)
    if (os.path.splitext(full_path)[1] in ['.srt','.sub']):
      subtitle_list.append(full_path)
  
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

log( __name__ ,"params: %s" % (params))

if params['action'] == 'search':
  log( __name__, "action 'search' called")
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
  
  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
  
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
  ## we pickup all our arguments sent from def Search()
  subs = Download(params["ID"],params["link"],params["filename"])
  ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
  
  
xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC
  
  
  
  
  
  
  
  
  
    

# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
from xbmc import log
import mechanize
import cookielib
import re, string, time
from BeautifulSoup import BeautifulSoup

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


def getmediaUrl(mediaArgs):
    title = re.sub(" \(?(.*.)\)", "", mediaArgs[1])
    if mediaArgs[2] != "":
      query = "site:altyazi.org inurl:sub/m \"%s ekibi\" intitle:\"%s\" intitle:\"(%s)\"" % (mediaArgs[0], title, mediaArgs[2])
    else:
      query = "site:altyazi.org inurl:sub/m \"%s ekibi\" intitle:\"%s\"" % (mediaArgs[0], title)
    br = mechanize.Browser()
    log("Divxplanet: Finding media %s" % query)
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    br.open("http://www.google.com")
    # Select the search box and search for 'foo'
    br.select_form( 'f' )
    br.form[ 'q' ] = query
    br.submit()
    page = br.response().read()
    soup = BeautifulSoup(page)

    linkdictionary = []
    query.replace(" ", "-")
    for li in soup.findAll('li', attrs={'class':'g'}):
        sLink = li.find('a')
        sSpan = li.find('span', attrs={'class':'st'})
        if sLink:
            linkurl = re.search(r"/url\?q=(http://altyazi.org//sub/m/[0-9]{3,8}/.*.\.html).*", sLink["href"])
            if linkurl:
                linkdictionary.append({"text": sSpan.getText().encode('utf8'), "name": mediaArgs[0], "url": linkurl.group(1)})
                log("Divxplanet: found media: %s" % (linkdictionary[0]["url"]))
    if len(linkdictionary) > 0:
      return linkdictionary[0]["url"]
    else:
      return ""

def Search(item):
#def search_subtitles(tvshow, year, season, episode, title): #standard input
    tvshow = item["tvshow"]
    year = item["year"]
    season = item["season"]
    episode = item["episode"]
    title = item["title"]

    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log("Divxplanet: searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        tvurl = getmediaUrl(["dizi",tvshow, year])
        log("Divxplanet: got media url %s" % (tvurl))
        if tvurl != "":
          divpname = re.search(r"http://altyazi.org//sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)
          season = int(season)
          episode = int(episode)
          # Browser
          br = mechanize.Browser()

          # Cookie Jar
          cj = cookielib.LWPCookieJar()
          br.set_cookiejar(cj)

          # Browser options
          br.set_handle_equiv(True)
          # br.set_handle_gzip(True)
          br.set_handle_redirect(True)
          br.set_handle_referer(True)
          br.set_handle_robots(False)

          # Follows refresh 0 but not hangs on refresh > 0
          br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

          # User-Agent (this is cheating, ok?)
          br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

          url = br.open(tvurl)
          html = url.read()
          soup = BeautifulSoup(html)
          subtitles_list = []
          i = 0
          # /sub/s/281212/Hannibal.html
          for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
              addr = link.get('href')
              info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
              if info:
                  tse = info[0].div.findAll("b", text="%d" % season)
                  tep = info[0].div.findAll("b", text="%02d" % episode)
                  lantext = link.parent.find("br")
                  lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                  if tse and tep and lan and lantext:
                      language = lan[0]["title"]
                      if language[0] == "e":
                          language = "English"
                          lan_short = "en"
                      else:
                          language = "Turkish"
                          lan_short = "tr"
                      filename = "%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short)
                      description = info[1].getText().encode('utf8')
                      listitem = xbmcgui.ListItem(label=language,                                   # language name for the found subtitle
                                label2=description,               # file name for the found subtitle
                                iconImage="0",                                     # rating for the subtitle, string 0-5
                                thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
                                )
                      listitem.setProperty( "hearing_imp", '{0}'.format("false").lower() ) # set to "true" if subtitle is for hearing impared
                      subtitles_list.append(listitem)
                      url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" % (__scriptid__,
                                                                      addr,
                                                                      lan_short,
                                                                      filename)
                      xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
          br.close()
          log("Divxplanet: found %d subtitles" % (len(subtitles_list)))
    else:
        log("Divxplanet: searching subtitles for %s %s" % (title, year))
        tvurl = getmediaUrl(["film", title, year])
        if tvurl == '':
         tvurl = getmediaUrl(["film", title, int(year)+1])
         log("Divxplanet: searching subtitles for %s %s" % (title, int(year)+1))
        if tvurl == '':
         tvurl = getmediaUrl(["film", title, int(year)-1])
         log("Divxplanet: searching subtitles for %s %s" % (title, int(year)-1))
        log("Divxplanet: got media url %s" % (tvurl))
        divpname = re.search(r"http://altyazi.org/sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            if info:
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                if lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    description = "no-description"
                    if info[0].getText() != "":
                      description = info[0].getText().encode('utf8')
                    filename = "%s.%s" % (title, lan_short)
                    log("Divxplanet: found a subtitle with description: %s" % (description))
                    listitem = xbmcgui.ListItem(label=language,                                   # language name for the found subtitle
                              label2=description,               # file name for the found subtitle
                              iconImage="0",                                     # rating for the subtitle, string 0-5
                              thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
                              )
                    listitem.setProperty( "hearing_imp", '{0}'.format("false").lower() ) # set to "true" if subtitle is for hearing impared
                    subtitles_list.append(listitem)
                    url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" % (__scriptid__,
                                                                    addr,
                                                                    lan_short,
                                                                    filename)
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
        br.close()
        log("Divxplanet: found %d subtitles" % (len(subtitles_list)))

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def Download(link, lang, filename): #standard input

    log("Divxplanet: o yoldayiz %s" % (link))
    subtitle_list = []
    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    #if xbmcvfs.exists(__temp__):
     # shutil.rmtree(__temp__)
    #xbmcvfs.mkdirs(__temp__)

    packed = True
    dlurl = "http://altyazi.org/%s" % link
    language = lang
    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    html = br.open(dlurl).read()
    br.select_form(name="dlform")
    r=br.submit()
    if r.info().has_key('Content-Disposition'):
        # If the response has Content-Disposition, we take file name from it
        localName = r.info()['Content-Disposition'].split('filename=')[1]
        if localName[0] == '"' or localName[0] == "'":
            localName = localName[1:-1]
    elif r.url != dlurl:
        # if we were redirected, the real file name we take from the final URL
        localName = url2name(r.url)



    log("Divxplanet: Fetching subtitles using url %s" % (dlurl))
    local_tmp_file = os.path.join(__temp__, localName )

    try:
        log("Divxplanet: Saving subtitles to '%s'" % (local_tmp_file))
        if not os.path.exists(__temp__):
            os.makedirs(__temp__)
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(br.response().get_data())
        local_file_handle.close()
    except:
        log("Divxplanet: Failed to save subtitle to %s" % (local_tmp_file))
    if packed:
        files = os.listdir(__temp__)
        init_filecount = len(files)
        max_mtime = 0
        filecount = init_filecount
        # determine the newest file from __temp__
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
                mtime = os.stat(os.path.join(__temp__, file)).st_mtime
                if mtime > max_mtime:
                    max_mtime =  mtime
        init_max_mtime = max_mtime
        time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + __temp__ +")")
        waittime  = 0
        while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
            time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
            files = os.listdir(__temp__)
            filecount = len(files)
            # determine if there is a newer file created in __temp__ (marks that the extraction had completed)
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub']):
                    mtime = os.stat(os.path.join(__temp__, file)).st_mtime
                    if (mtime > max_mtime):
                        max_mtime =  mtime
            waittime  = waittime + 1
        if waittime == 20:
            log("Divxplanet: Failed to unpack subtitles in '%s'" % (__temp__))
        else:
            log("Divxplanet: Unpacked files in '%s'" % (__temp__))
            for file in files:
                # there could be more subtitle files in __temp__, so make sure we get the newly created subtitle file
                if (string.split(file, '.')[-1] in ['srt', 'sub']) and (os.stat(os.path.join(__temp__, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                    log("Divxplanet: Unpacked subtitles file '%s'" % (file.encode("utf-8")))
                    subs_file = os.path.join(__temp__, file)
                    subtitle_list.append(subs_file)
    log("Divxplanet: Subtitles saved to '%s'" % ( local_tmp_file))
    br.close()
    return subtitle_list


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
  #log("Divxplanet: %s" % xbmc.Player().getVideoInfoTag().getIMDBNumber())

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
  ## we pickup all our arguments sent from def Search()
  subs = Download(params["link"],params["lang"], params["description"])
  ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC

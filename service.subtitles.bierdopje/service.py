# -*- coding: UTF-8 -*-

import os, sys, re, string, urllib, urllib2, time, unicodedata, xml.etree.ElementTree as XMLTree
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs

try: import simplejson as json
except: import json

__addon__      = xbmcaddon.Addon()
__scriptid__   = __addon__.getAddonInfo('id')
__version__    = __addon__.getAddonInfo('version')
__name__       = __addon__.getAddonInfo('name')
__language__   = __addon__.getLocalizedString
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

useragent        = __name__ + '/' + __version__
apiurl           = "http://api.bierdopje.com/"
apikey           = "369C2ED4261DE9C3"
showids_filename = os.path.join( __profile__ ,"bierdopje_show_ids.txt" )
sleeptime        = 0.6
releases_types   = ['web-dl', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'aac20', 'hdtv', 'dvdrip', 'ac3', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']
overloaded       = False

#====================================================================================================================
# Functions
#====================================================================================================================

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii','ignore')

def getShowId():
    try:
        playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
        tvshowid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
        tvshowid = json.loads(xbmc.executeJSONRPC (tvshowid_query))['result']['item']['tvshowid']
        tvdbid_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
        return json.loads(xbmc.executeJSONRPC (tvdbid_query))['result']['tvshowdetails']['imdbnumber']
    except:
        log( __name__ ," Failed to find TVDBid in database")

def apicall(command, paramslist):
    global overloaded
    time.sleep(sleeptime)
    url = apiurl + apikey + "/" + command
    for param in paramslist:
        url = url + "/" + urllib.quote_plus(param)
    log( __name__ ," getting url '%s'" % url )
    try:
        request = urllib2.Request(url)
        request.add_header("User-agent", useragent)
        response = urllib2.urlopen(request)
    except IOError, e:
        if hasattr(e, 'reason'):
            log( __name__ ," failed to reach Bierdopje site, reason: '%s'." % e.reason )
            okdialog = xbmcgui.Dialog()
            # ok = okdialog.ok("Error", "Failed to reach Bierdopje.com: '%s'." % e.reason)
            ok = okdialog.ok(__language__(32001), __language__(32002) + ": '%s'." % e.reason)
        elif hasattr(e, 'code'):
            if e.code == 429: # HTTP Error 429 means: "Too Many Requests"
                log( __name__ ," Bierdopje is overloaded (HTTP error 429: Too many requests). Reply from bierdopje:\n%s" % e.read() )
                overloaded = True
            else:
                log( __name__ ," Bierdopje site couldn't fulfill the request, HTTP code: '%s'." % e.code )
                okdialog = xbmcgui.Dialog()
                # ok = okdialog.ok("Error", "Bierdopje couldn't fulfill the request, HTTP code: '%s'." % e.code)
                ok = okdialog.ok(__language__(32001), __language__(32003) + ": '%s'." % e.code)
        else:
            log( __name__ ," unkown error while contacting Bierdopje site")
            okdialog = xbmcgui.Dialog()
            # ok = okdialog.ok("Error", "Unkown error while contacting Bierdopje.com")
            ok = okdialog.ok(__language__(32001), __language__(32004))
    else:
        try:
            xml = XMLTree.parse(response)
            status = gettextelements(xml, "response/status")
        except:
            okdialog = xbmcgui.Dialog()
            # ok = okdialog.ok("Error", "Unexpected response from Bierdopje.com")
            ok = okdialog.ok(__language__(32001), __language__(32005))
            log( __name__ ," unexpected response from Bierdopje site.")
            return None
        if status == ["false"]:
            log( __name__ ," failed to get proper response from Bierdopje site (status = false)")
            return None
        else:
            return xml

def gettextelements(xml, path):
    textelements = []
    try:
        elements = xml.findall(path)
    except:
        return
    for element in elements:
        textelements.append(element.text)
    return textelements

def getshowid(showname):
    showid = None
    showids = {}
    if os.path.isfile(showids_filename):
        showids_filedata = file(showids_filename,'r').read()
        showids = eval(showids_filedata)
        if showname in showids:
            log( __name__ ," show id for '%s' is '%s' (from cachefile '%s')" % (showname, showids[showname], showids_filename))
            return showids[showname]
    if showid is None:
        tvdbid = getShowId()
        if tvdbid:
            if not overloaded:
                response = apicall("GetShowByTVDBID",[tvdbid])
            if overloaded:
                return None
            if response is not None:
                showid = gettextelements(response,"response/showid")
                if len(showid) == 1:
                    log( __name__ ," show id for '%s' is '%s' (found by TVDBid %s)" % (showname, str(showid[0]), tvdbid))
                    showids[showname] = str(showid[0])
                    file(showids_filename,'w').write(repr(showids))
                    return str(showid[0])
    if not overloaded:
        response = apicall("GetShowByName",[showname])
    if overloaded:
        return None
    if response is not None:
        showid = gettextelements(response,"response/showid")
        if len(showid) == 1:
            log( __name__ ," show id for '%s' is '%s'" % (showname, str(showid[0])) )
            showids[showname] = str(showid[0])
            file(showids_filename,'w').write(repr(showids))
            return str(showid[0])
    if (showid is None) and ("'" in showname):
        if not overloaded:
            response = apicall("GetShowByName",[string.replace(showname,"'","''")])
        if overloaded:
            return None
        if response is not None:
            showid = gettextelements(response,"response/showid")
            if len(showid) == 1:
                log( __name__ ," show id for '%s' is '%s' (replaced ' with '')" % (string.replace(showname,"'","''"), str(showid[0])) )
                showids[showname] = str(showid[0])
                file(showids_filename,'w').write(repr(showids))
                return str(showid[0])
    okdialog = xbmcgui.Dialog()
    # ok = okdialog.ok("Error", "Failed to get a show id from Bierdopje for " + showname)
    ok = okdialog.ok(__language__(32001), __language__(32006) + " " + showname)
    log( __name__ ," failed to get a show id for '%s'" % showname )
    return None

def getrating(subsfile, videofile):
    rating = 0
    videofile = "".join(string.split(videofile, '.')[:-1])
    videofile = string.lower(videofile)
    subsfile = string.lower(subsfile)
    videofile = string.replace(videofile, '.', '')
    subsfile = string.replace(subsfile, '.', '')
    for release_type in releases_types:
        if (release_type in videofile) and (release_type in subsfile): rating += 1
    if string.split(videofile, '-')[-1] == string.split(subsfile, '-')[-1] : rating += 1
    if rating > 0:
        rating = rating * 2 - 1
        if rating > 9: rating = 9
    return rating

def isexactmatch(subsfile, videofile):
    videofile = "".join(string.split(videofile, '.')[:-1])
    videofile = string.lower(videofile)
    videofile = string.replace(videofile, ' ', '.')
    videofile = string.replace(videofile, '.', '')
    subsfile = string.replace(subsfile, '.', '')
    subsfile = string.lower(subsfile)
    log( __name__ ," comparing subtitle file with videofile (sync?):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (subsfile, videofile) )
    if string.find(subsfile, videofile) > -1:
        log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (subsfile) )
        return True
    else:
        # try to strip the episode title from the videofile and compare again
        episodetitle = None
        for release_type in releases_types:
            match = re.search("s\d\de\d\d(.+)" + release_type, videofile)
            if match:
                if episodetitle is None: episodetitle = match.group(1)
                elif len(episodetitle) > len(match.group(1)): episodetitle = match.group(1)
        if (episodetitle not in releases_types) and (episodetitle is not None):
            log( __name__ ," found episodetitle: '%s'" % (episodetitle))
            videofile = string.replace(videofile, episodetitle, '')
            log( __name__ ," comparing subtitle file with videofile, excluding episode title (sync?):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (subsfile, videofile) )
            if string.find(subsfile, videofile) > -1:
                log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
                return True
            else:
                return False

def getallsubs(showid, file_original_path, tvshow, season, episode, languageshort, languagelong, subtitles_list):
    not_sync_list = []
    if not overloaded:
        response = apicall("GetAllSubsFor",[showid, str(season), str(episode), languageshort])
    if overloaded:
        response = None
    if response is not None:
        filenames = gettextelements(response,"response/results/result/filename")
        downloadlinks = gettextelements(response,"response/results/result/downloadlink")
        if len(filenames) > 0:
            log( __name__ ," found %s %s subtitles" % (len(filenames), languagelong))
            for i in range(len(filenames)):
                if string.lower(filenames[i][-4:]) == ".srt":
                    filenames[i] = filenames[i][:-4]
                if isexactmatch(filenames[i], os.path.basename(file_original_path)):
                    sync = True
                    rating = 10
                else:
                    sync = False
                    rating = getrating(filenames[i], os.path.basename(file_original_path))
                # subtitles_list.append({'rating': str(rating), 'no_files': 1, 'format': 'srt', 'movie':  tvshow, 'language_id': '', 'filename': filenames[i], 'sync': sync, 'link': downloadlinks[i], 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong, 'ID': '0'})
                subtitles_list.append({'lang_index'    : 0,
                      'filename'      : filenames[i],
                      'link'          : downloadlinks[i],
                      'language_name' : languagelong,
                      'language_flag' : languageshort,
                      'language_id'   : '',
                      'ID'            : 0,
                      'rating'        : str(int(round(float(rating/2)))),
                      'format'        : 'srt',
                      'sync'          : sync,
                      'hearing_imp'   : 0
                      })
        else:
            log( __name__ ," found no %s subtitles" % (languagelong))

def search_subtitles( file_original_path, title, tvshow, year, season, episode, languages):
    subtitles_list = []
    if len(tvshow) > 0:
        tvshow_id= getshowid(tvshow)
        if tvshow_id is not None:
            dutch = 0
            english = 0
            if 'dut' in languages: dutch = 1
            if 'eng' in languages: english = 1
            if dutch > 0:
                getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "nl", "Dutch", subtitles_list)
            if english > 0:
                getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "en", "English", subtitles_list)
            subtitles_list.sort(key=lambda x: [ x['sync'], x['rating']], reverse = True)
            if ((dutch == 1) and (english == 1)):
                subtitles_list.sort(key=lambda x: [ x['language_name']])
            if ((dutch == 0) and (english == 0)):
                okdialog = xbmcgui.Dialog()
                # ok = okdialog.ok("Error", "Bierdopje is only for Dutch and English subtitles")
                ok = okdialog.ok(__language__(32001), __language__(32007))
    else:
        okdialog = xbmcgui.Dialog()
        # ok = okdialog.ok("Error", "Bierdopje only works with tv shows in library mode")
        ok = okdialog.ok(__language__(32001), __language__(32008))
    if overloaded:
        okdialog = xbmcgui.Dialog()
        # ok = okdialog.ok("Error", "Bierdopje is currently overloaded (HTTP error 429: Too many requests). Please try again later")
        ok = okdialog.ok(__language__(32001), __language__(32009))
    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                      label2=it["filename"],
                                      iconImage=it["rating"],
                                      thumbnailImage=it["language_flag"]
                                      )
            if it["sync"]: listitem.setProperty( "sync", "true" )
            else: listitem.setProperty( "sync", "false" )
            listitem.setProperty( "hearing_imp", "false" )
            url = "plugin://%s/?action=download&link=%s&ID=%s&filename=%s" % (__scriptid__, it["link"], it["ID"],it["filename"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

def download_subtitles (link, filename):
    local_tmp_file = os.path.join(__temp__, "bierdopje_subs.srt")
    log( __name__ ," downloading subtitles from url '%s'" % link )
    try:
        request = urllib2.Request(link)
        request.add_header("User-agent", useragent)
        response = urllib2.urlopen(request)
    except:
        okdialog = xbmcgui.Dialog()
        # ok = okdialog.ok("Error", "Failed to contact Bierdopje.com")
        ok = okdialog.ok(__language__(32001), __language__(32010))
        log( __name__ ," failed to get url '%s'" % link )
    else:
        log( __name__ ," saving subtitles to '%s'" % local_tmp_file )
        try:
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            okdialog = xbmcgui.Dialog()
            # ok = okdialog.ok("Error", "Failed to save subtitles")
            ok = okdialog.ok(__language__(32001), __language__(32011))
            log( __name__ ," failed to save subtitles to '%s'" % local_tmp_file )
        else:
            if xbmcvfs.exists(local_tmp_file):
                listitem = xbmcgui.ListItem(label=local_tmp_file)
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=local_tmp_file,listitem=listitem,isFolder=False)

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

def search():
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
    item['3let_language']      = []                                                              # ['scc','eng']
    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
    if item['title'] == "":
        log( __name__, "VideoPlayer.OriginalTitle not found")
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
    if item['episode'].lower().find("s") > -1:                                        # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]
    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True
    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])
    log( __name__, item)
    search_subtitles( item['file_original_path'], item['title'], item['tvshow'], item['year'], item['season'], item['episode'], item['3let_language'])

#====================================================================================================================
# Main
#====================================================================================================================

params = get_params()
log( __name__, params)

if not xbmcvfs.exists(__temp__):
    xbmcvfs.mkdirs(__temp__)

if params['action'] == 'search': search()
elif params['action'] == 'download': download_subtitles(params["link"],params["filename"])

xbmcplugin.endOfDirectory(int(sys.argv[1]))

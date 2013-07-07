# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, xbmcaddon, string, urllib, urllib2, time, xml.etree.ElementTree as XMLTree
from utilities import log, getShowId

_                = sys.modules[ "__main__" ].__language__
__profile__      = sys.modules[ "__main__" ].__profile__
__version__      = sys.modules[ "__main__" ].__version__

useragent        = 'script.xbmc.subtitles/' + __version__
apiurl           = "http://api.bierdopje.com/"
apikey           = "369C2ED4261DE9C3"
showids_filename = os.path.join( __profile__ ,"bierdopje_show_ids.txt" )
sleeptime        = 0.6
releases_types   = ['web-dl', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'aac20', 'hdtv', 'dvdrip', 'ac3', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']
overloaded       = False

#====================================================================================================================
# Functions
#====================================================================================================================

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
            ok = okdialog.ok("Error", "Failed to reach Bierdopje: '%s'." % e.reason)
        elif hasattr(e, 'code'):
            if e.code == 429: # HTTP Error 429 means: "Too Many Requests"
                log( __name__ ," Bierdopje is overloaded (HTTP error 429: Too many requests). Reply from bierdopje:\n%s" % e.read() )
                overloaded = True
            else:
                log( __name__ ," Bierdopje site couldn't fulfill the request, HTTP code: '%s'." % e.code )
                okdialog = xbmcgui.Dialog()
                ok = okdialog.ok("Error", "Bierdopje couldn't fulfill the request, HTTP code: '%s'." % e.code)
        else:
            log( __name__ ," unkown error while contacting Bierdopje site")
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Unkown error while contacting Bierdopje.")
    else:
        try:
            xml = XMLTree.parse(response)
            status = gettextelements(xml, "response/status")
        except:
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "unexpected response from Bierdopje.")
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
    ok = okdialog.ok("Error", "Failed to get a show id from Bierdopje for " + showname)
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
                subtitles_list.append({'rating': str(rating), 'no_files': 1, 'format': 'srt', 'movie':  tvshow, 'language_id': '', 'filename': filenames[i], 'sync': sync, 'link': downloadlinks[i], 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong, 'ID': '0'})
        else:
            log( __name__ ," found no %s subtitles" % (languagelong))

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
        tvshow_id= getshowid(tvshow)
        if tvshow_id is not None:
            dutch = 0
            if string.lower(lang1) == "dutch": dutch = 1
            elif string.lower(lang2) == "dutch": dutch = 2
            elif string.lower(lang3) == "dutch": dutch = 3
            english = 0
            if string.lower(lang1) == "english": english = 1
            elif string.lower(lang2) == "english": english = 2
            elif string.lower(lang3) == "english": english = 3
            if dutch > 0:
                getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "nl", "Dutch", subtitles_list)
            if english > 0:
                getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "en", "English", subtitles_list)
            subtitles_list.sort(key=lambda x: [ x['sync'], x['rating']], reverse = True)
            if ((dutch > 0) and (english > 0) and (dutch < english)):
                subtitles_list.sort(key=lambda x: [ x['language_name']])
            if ((dutch > 0) and (english > 0) and (dutch > english)):
                subtitles_list.sort(key=lambda x: [ x['language_name']], reverse = True)
            if ((dutch == 0) and (english == 0)):
                msg = "Won't work, Bierdopje is only for Dutch and English subtitles."
    else:
        msg = "Won't work, Bierdopje is only for tv shows."
    if overloaded:
        msg = _(755)
    return subtitles_list, "", msg #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    local_tmp_file = os.path.join(tmp_sub_dir, "bierdopje_subs.srt")

    log( __name__ ," downloading subtitles from url '%s'" % subtitles_list[pos][ "link" ] )
    try:
        request = urllib2.Request(subtitles_list[pos][ "link" ])
        request.add_header("User-agent", useragent)
        response = urllib2.urlopen(request)
    except:
        okdialog = xbmcgui.Dialog()
        ok = okdialog.ok("Error", "Failed to contact Bierdopje site.")
        log( __name__ ," failed to get url '%s'" % subtitles_list[pos][ "link" ] )
    else:
        log( __name__ ," saving subtitles to '%s'" % local_tmp_file )
        try:
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Failed to save subtitles.")
            log( __name__ ," failed to save subtitles to '%s'" % local_tmp_file )
        else:
            language = subtitles_list[pos][ "language_name" ]
            return False, language, local_tmp_file #standard output

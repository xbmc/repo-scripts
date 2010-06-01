import os, sys, re, xbmc, xbmcgui, string, urllib, ElementTree as XMLTree

_ = sys.modules[ "__main__" ].__language__

apiurl   = "http://api.bierdopje.com/"
apikey   = "369C2ED4261DE9C3"

#====================================================================================================================
# Functions
#====================================================================================================================

def apicall(command, paramslist):
    url = apiurl + apikey + "/" + command
    for param in paramslist:
        url = url + "/" + urllib.quote_plus(param)
    xbmc.output("Bierdopje subtitle service: getting url '%s'" % url,level=xbmc.LOGDEBUG )
    try:
        response = urllib.urlopen(url)
    except:
        okdialog = xbmcgui.Dialog()
        ok = okdialog.ok("Error", "Failed to contact Bierdopje site.")
        xbmc.output("Bierdopje subtitle service: failed to get url '%s'" % url,level=xbmc.LOGDEBUG )
    else:
        try:
            xml = XMLTree.parse(response)
            status = gettextelements(xml, "response/status")
        except:
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Failed to contact Bierdopje site.")
            xbmc.output("Bierdopje subtitle service: failed to get proper response for url '%s'" % url,level=xbmc.LOGDEBUG )
            return None
        if status == "false":
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Failed to contact Bierdopje site.")
            xbmc.output("Bierdopje subtitle service: failed to get proper response (status = false) for url '%s'" % url,level=xbmc.LOGDEBUG )
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
    response = apicall("GetShowByName",[showname])
    if response is not None:
        showid = gettextelements(response,"response/showid")
        if len(showid) == 1:
            xbmc.output("Bierdopje subtitle service: show id for '%s' is '%s'" % (showname, str(showid[0])),level=xbmc.LOGDEBUG )
            return str(showid[0])
        else:
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Failed to get a show id from Bierdopje for " + showname)
            xbmc.output("Bierdopje subtitle service: failed to get a show id for '%s'" % showname,level=xbmc.LOGDEBUG )
        

def isexactmatch(subsfile, moviefile):
    match = re.match("(.*)\.", moviefile)
    if match:
        moviefile = string.lower(match.group(1))
        subsfile = string.lower(subsfile)
        xbmc.output("Bierdopje subtitle service: comparing subtitle file with moviefile to see if it is a match (sync):\nsubtitlesfile  = '%s'\nmoviefile      = '%s'" % (string.lower(subsfile), string.lower(moviefile)),level=xbmc.LOGDEBUG )
        if string.find(string.lower(subsfile),string.lower(moviefile)) > -1:
            xbmc.output("Bierdopje subtitle service: found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)),level=xbmc.LOGDEBUG )
            return True
        else:
            return False
    else:
        return False

def getallsubs(showid, file_original_path, tvshow, season, episode, languageshort, languagelong, subtitles_list):
    not_sync_list = []
    response = apicall("GetAllSubsFor",[showid, str(season), str(episode), languageshort])
    if response is not None:
        filenames = gettextelements(response,"response/results/result/filename")
        downloadlinks = gettextelements(response,"response/results/result/downloadlink")
        if len(filenames) > 0:
            xbmc.output("Bierdopje subtitle service: found %s %s subtitles" % (len(filenames), languagelong), level=xbmc.LOGDEBUG )
            for i in range(len(filenames)):
                if string.lower(filenames[i][-4:]) == ".srt":
                    filenames[i] = filenames[i][:-4]
                sync = False
                if isexactmatch(filenames[i], os.path.basename(file_original_path)):
                    sync = True
                    subtitles_list.append({'rating': '0', 'no_files': 1, 'format': 'srt', 'movie':  tvshow, 'language_id': '', 'filename': filenames[i], 'sync': sync, 'link': downloadlinks[i], 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong, 'ID': '0'})
                else:
                    not_sync_list.append({'rating': '0', 'no_files': 1, 'format': 'srt', 'movie':  tvshow, 'language_id': '', 'filename': filenames[i], 'sync': sync, 'link': downloadlinks[i], 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong, 'ID': '0'})
            for i in range(len(not_sync_list)):
                subtitles_list.append(not_sync_list[i])
        else:
            xbmc.output("Bierdopje subtitle service: found no %s subtitles" % (languagelong), level=xbmc.LOGDEBUG )


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
        tvshow_id= getshowid(tvshow)
        dutch = 0
        if string.lower(lang1) == "dutch": dutch = 1
        elif string.lower(lang2) == "dutch": dutch = 2
        elif string.lower(lang3) == "dutch": dutch = 3

        english = 0
        if string.lower(lang1) == "english": english = 1
        elif string.lower(lang2) == "english": english = 2
        elif string.lower(lang3) == "english": english = 3

        if ((dutch > 0) and (english == 0)):
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "nl", "Dutch", subtitles_list)

        if ((english > 0) and (dutch == 0)):
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "en", "English", subtitles_list)

        if ((dutch > 0) and (english > 0) and (dutch < english)):
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "nl", "Dutch", subtitles_list)
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "en", "English", subtitles_list)

        if ((dutch > 0) and (english > 0) and (dutch > english)):
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "en", "English", subtitles_list)
            getallsubs(tvshow_id, file_original_path, tvshow, season, episode, "nl", "Dutch", subtitles_list)

        if ((dutch == 0) and (english == 0)):
            msg = "Won't work, Bierdopje is only for Dutch and English subtitles."
    else:
        msg = "Won't work, Bierdopje is only for tv shows."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    local_tmp_file = os.path.join(tmp_sub_dir, "bierdopje_subs.srt")

    xbmc.output("Bierdopje subtitle service: downloading subtitles from url '%s'" % subtitles_list[pos][ "link" ],level=xbmc.LOGDEBUG )
    try:
        response = urllib.urlopen(subtitles_list[pos][ "link" ])
    except:
        okdialog = xbmcgui.Dialog()
        ok = okdialog.ok("Error", "Failed to contact Bierdopje site.")
        xbmc.output("Bierdopje subtitle service: failed to get url '%s'" % subtitles_list[pos][ "link" ],level=xbmc.LOGDEBUG )
    else:
        xbmc.output("Bierdopje subtitle service: saving subtitles to '%s'" % local_tmp_file,level=xbmc.LOGDEBUG )
        try:
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            okdialog = xbmcgui.Dialog()
            ok = okdialog.ok("Error", "Failed to save subtitles.")
            xbmc.output("Bierdopje subtitle service: failed to save subtitles to '%s'" % local_tmp_file,level=xbmc.LOGDEBUG )
        else:
            language = subtitles_list[pos][ "language_name" ]
            return False, language, local_tmp_file #standard output

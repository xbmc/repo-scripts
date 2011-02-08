import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.undertexter.se/"
eng_download_url = "http://eng.undertexter.se/"
debug_pretext = ""

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
                                            <a href="http://www.undertexter.se/?p=undertext&id=20093" alt="Julie & Julia (Julie and Julia)" title="Julie & Julia (Julie and Julia)"><b>
                                            Julie & Julia (Julie and Julia)</b>
                                            </a></td>
                                        </tr>
                                        <tr>
                                          <td colspan="2" align="left" valign="top" bgColor="#f2f2f2"  style="padding-top: 0px; padding-left: 4px; padding-right: 0px; padding-bottom: 0px; border-bottom: 1px solid rgb(153, 153, 153); border-color: #E1E1E1" >
                                            (1 cd)
                                                                                        <br> <img src="bilder/spacer.gif" height="2"><br>

                                            Nedladdningar: 316<br>
                                            <img src="bilder/spacer.gif" height="3"><br>
                                            Julie.&.Julia.2009.720p.BluRay.DTS.x264-EbP</td>
                                        </tr>

"""
subtitle_pattern = "<a href=\"http://www.undertexter.se/\?p=[^ \r\n\t]*?&id=(\d{1,10})\" alt=\"[^\r\n\t]*?\" title=\"[^\r\n\t]*?\"><b>\
[ \r\n]*?[^\r\n\t]*?</b>.{400,500}?\(1 cd\).{250,550}?[ \r\n]*([^\r\n\t]*?)</td>[ \r\n]*?[^\r\n\t]*?</tr>"


# group(1) = id, group(2) = filename


#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, subtitles_list):
    if languageshort == "sv":
        url = main_url + "?group1=on&p=soek&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
    if languageshort == "en":
        url = main_url + "?group1=on&p=eng_search&add=arkiv&submit=S%F6k&select2=&select3=&select=&str=" + urllib.quote_plus(searchstring)
    content = geturl(url)
    if content is not None:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            filename = string.strip(matches.group(2))
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content = response.read()
        return_url = response.geturl()
        if url != return_url:
            log( __name__ ,"%s Getting redirected url: %s" % (debug_pretext, return_url))
            if (' ' in return_url):
                log( __name__ ,"%s Redirected url contains space (workaround a bug in python redirection: 'http://bugs.python.org/issue1153027', should be solved, but isn't)" % (debug_pretext))
                return_url = return_url.replace(' ','%20')
            response = my_urlopener.open(return_url)
            content = response.read()
            return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    swedish = 0
    if string.lower(lang1) == "swedish": swedish = 1
    elif string.lower(lang2) == "swedish": swedish = 2
    elif string.lower(lang3) == "swedish": swedish = 3

    english = 0
    if string.lower(lang1) == "english": english = 1
    elif string.lower(lang2) == "english": english = 2
    elif string.lower(lang3) == "english": english = 3

    if ((swedish > 0) and (english == 0)):
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

    if ((english > 0) and (swedish == 0)):
        getallsubs(searchstring, "en", "English", subtitles_list)

    if ((swedish > 0) and (english > 0) and (swedish < english)):
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)
        getallsubs(searchstring, "en", "English", subtitles_list)

    if ((swedish > 0) and (english > 0) and (swedish > english)):
        getallsubs(searchstring, "en", "English", subtitles_list)
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

    if ((swedish == 0) and (english == 0)):
        msg = "Won't work, Undertexter.se is only for Swedish and English subtitles."

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    if string.lower(language) == "swedish":
        url = main_url + "laddatext.php?id=" + id
    if string.lower(language) == "english":
        url = eng_download_url + "download.php?id=" + id
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "undertexter.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                if mtime > max_mtime:
                    max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

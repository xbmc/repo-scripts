import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://swesub.nu/"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<img src='e107_themes/memnockChristmasMod/images/bullet2.gif' alt='' style='vertical-align: middle' /> <b><a class='visit' href='download.php?view.23644'>A Christmas Carol - En julsaga</a></b><br /><div class='smalltext'><a href='download.php?list.'></a></div>Disney's.A.Christmas.Carol.2010.1080p.MKV.AC3.DTS....<br /><span class='smalltext'>Datum: söndag 28 november 2010 - 22:36:38</span><br /><br />
"""
subtitle_pattern = "<a class=\'visit\' href=\'download\.php\?view\.(\d{1,10})\'>[^\r\n\t]*?</a></b><br /><div class=\'smalltext\'><a href=\'download\.php\?list\.\'></a></div>([^\r\n\t]*?)<br /><span class=\'smalltext\'>"
# group(1) = id, group(2) = filename

#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, subtitles_list):
    url = main_url + "search.php?q=&r=0&s=S%F6k&in=" + urllib.quote_plus(searchstring) + "&ex=&ep=&be=" + urllib.quote_plus(searchstring) + "&adv=0"
    content = geturl(url)
    if content is not None:
        log( __name__ ,"Getting '%s' subs ..." % (languageshort))
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            filename = string.strip(matches.group(2))
            log( __name__ ,"Subtitles found: %s (id = %s)" % (filename, id))
            subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"Getting url: %s" % (url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,"Search string = %s" % (searchstring))

    swedish = 0
    if string.lower(lang1) == "swedish": swedish = 1
    elif string.lower(lang2) == "swedish": swedish = 2
    elif string.lower(lang3) == "swedish": swedish = 3

    if (swedish > 0):
        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

    if (swedish == 0):
        msg = "Won't work, Swesub.nu is only for Swedish subtitles."

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    url = main_url + "request.php?" + id
    log( __name__ ,"Fetching subtitles using url %s" % (url))
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.zip")
            packed = True                   
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))
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
                log( __name__ ,"Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
            else:
                log( __name__ ,"Unpacked files in '%s'" % (tmp_sub_dir))        
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"Unpacked subtitles file '%s'" % (file))        
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output
            
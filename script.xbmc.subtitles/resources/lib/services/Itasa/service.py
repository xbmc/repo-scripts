import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__

main_url = "http://www.italiansubs.net/"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

#<input type="hidden" name="return" value="aHR0cDovL3d3dy5pdGFsaWFuc3Vicy5uZXQv" /><input type="hidden" name="c10b48443ee5730c9b5a0927736bd09f" value="1" />
unique_pattern = '<input type="hidden" name="return" value="([^\n\r\t ]+?)" /><input type="hidden" name="([^\n\r\t ]+?)" value="([^\n\r\t ]+?)" />'
#<a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1170"> Castle</a>
show_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+&amp;func=select&amp;id=[^\n\r\t ]+?)"> %s</a>'
#href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1171"> Stagione 1</a>
season_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=select&amp;id=[^\n\r\t ]+?)"> Stagione %s</a>'
#<img src='http://www.italiansubs.net/components/com_remository/images/folder_icons/category.gif' width=20 height=20><a name="1172"><a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=select&amp;id=1172"> 720p</a>
category_pattern = '<img src=\'http://www\.italiansubs\.net/components/com_remository/images/folder_icons/category\.gif\' width=20 height=20><a name="[^\n\r\t ]+?"><a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=select&amp;id=[^\n\r\t ]+?)"> ([^\n\r\t]+?)</a>'
#<a href="http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=fileinfo&amp;id=7348">Dexter 3x02</a>
subtitle_pattern = '<a href="http://www\.italiansubs\.net/(index.php\?option=com_remository&amp;Itemid=\d+?&amp;func=fileinfo&amp;id=([^\n\r\t ]+?))">(%s %sx%02d.*?)</a>'
#<a href='http://www.italiansubs.net/index.php?option=com_remository&amp;Itemid=6&amp;func=download&amp;id=7228&amp;chk=5635630f675375afbdd6eec317d8d688&amp;no_html=1'>
subtitle_download_pattern = '<a href=\'http://www\.italiansubs\.net/(index\.php\?option=com_remository&amp;Itemid=\d+?&amp;func=download&amp;id=%s&amp;chk=[^\n\r\t ]+?&amp;no_html=1\')>'


#====================================================================================================================
# Functions
#====================================================================================================================

def geturl(url):
    log( __name__ , " Getting url: %s" % (url))
    try:
        response = urllib2.urlopen(url)
        content = response.read()
    except:
        log( __name__ , " Failed to get url:%s" % (url))
        content = None
    return(content)


def login(username, password):
    log( __name__ , " Logging in with username '%s' ..." % (username))
    content= geturl(main_url + 'index.php')
    if content is not None:
        match = re.search('logouticon.png', content, re.IGNORECASE | re.DOTALL)
        if match:
            return 1
        else:
            match = re.search(unique_pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return_value = match.group(1)
                unique_name = match.group(2)
                unique_value = match.group(3)
                login_postdata = urllib.urlencode({'username': username, 'passwd': password, 'remember': 'yes', 'Submit': 'Login', 'remember': 'yes', 'option': 'com_user', 'task': 'login', 'silent': 'true', 'return': return_value, unique_name: unique_value} )
                cj = cookielib.CookieJar()
                my_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
                urllib2.install_opener(my_opener)
                request = urllib2.Request(main_url + 'index.php',login_postdata)
                response = urllib2.urlopen(request).read()
                match = re.search('logouticon.png', response, re.IGNORECASE | re.DOTALL)
                if match:
                    return 1
                else:
                    return 0
    else:
        return 0


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
        italian = 0
        if (string.lower(lang1) == "italian") or (string.lower(lang2) == "italian") or (string.lower(lang3) == "italian"):
            username = __settings__.getSetting( "ITuser" )
            password = __settings__.getSetting( "ITpass" )
            if login(username, password):
                log( __name__ , " Login successful")
                content= geturl(main_url + 'index.php?option=com_remository&Itemid=6')
                if content is not None:
                    match = re.search(show_pattern % tvshow, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        log( __name__ ," Tv show '%s' found" % tvshow)
                        content= geturl(main_url + match.group(1))
                        if content is not None:
                            match = re.search(season_pattern % season, content, re.IGNORECASE | re.DOTALL)
                            if match:
                                log( __name__ ," Season %s of tv show '%s' found" % (season, tvshow))
                                category = 'normal'
                                categorypage = match.group(1)
                                content= geturl(main_url + categorypage)
                                if content is not None:
                                    for matches in re.finditer(subtitle_pattern % (tvshow, int(season), int(episode)), content, re.IGNORECASE | re.DOTALL):
                                        filename = matches.group(3)
                                        id = matches.group(2)
                                        log( __name__ ," Adding '%s' to list of subtitles" % filename)
                                        subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'link' : categorypage, 'language_flag': 'flags/it.gif', 'language_name': 'Italian'})
                                    for matches in re.finditer(category_pattern, content, re.IGNORECASE | re.DOTALL):
                                        categorypage = matches.group(1)
                                        category = matches.group(2)
                                        log( __name__ ," Page for category '%s' found" % category)
                                        content= geturl(main_url + categorypage)
                                        if content is not None:
                                            for matches in re.finditer(subtitle_pattern % (tvshow, int(season), int(episode)), content, re.IGNORECASE | re.DOTALL):
                                                id = matches.group(2)
                                                filename = matches.group(3)
                                                log( __name__ ," Adding '%s (%s)' to list of subtitles" % (filename, category))
                                                subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': "%s (%s)" % (filename, category), 'sync': False, 'id' : id, 'link' : categorypage, 'language_flag': 'flags/it.gif', 'language_name': 'Italian'})
                            else:
                                log( __name__ ," Season %s of tv show '%s' not found" % (season, tvshow))
                                msg = "Season %s of tv show '%s' not found" % (season, tvshow)
                    else:
                        log( __name__ ," Tv show '%s' not found." % tvshow)
                        msg = "Tv show '%s' not found" % tvshow
            else:
                log( __name__ ," Login to Itasa failed. Check your username/password at the addon configuration.")
                msg = "Login to Itasa failed. Check your username/password at the addon configuration."
        else:
            msg = "Won't work, Itasa is only for Italian subtitles."
    else:
        msg = "Won't work, Itasa is only for tv shows."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    username = __settings__.getSetting( "ITuser" )
    password = __settings__.getSetting( "ITpass" )
    if login(username, password):
        log( __name__ , " Login successful")
        id = subtitles_list[pos][ "id" ]
        link = subtitles_list[pos][ "link" ]
        content= geturl(main_url + link)
        match = re.search(subtitle_download_pattern % id, content, re.IGNORECASE | re.DOTALL)
        if match:
            language = subtitles_list[pos][ "language_name" ]
            log( __name__ ," Fetching subtitles using url %s" % (main_url + match.group(1)))
            content = geturl(main_url + match.group(1))
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
                log( __name__ ," Saving subtitles to '%s'" % (local_tmp_file))
                try:
                    local_file_handle = open(local_tmp_file, "wb")
                    local_file_handle.write(content)
                    local_file_handle.close()
                except:
                    log( __name__ ," Failed to save subtitles to '%s'" % (local_tmp_file))
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
                        log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
                    else:
                        log( __name__ ," Unpacked files in '%s'" % (tmp_sub_dir))
                        for file in files:
                            # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                            if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                                log( __name__ ," Unpacked subtitles file '%s'" % (file))
                                subs_file = os.path.join(tmp_sub_dir, file)
                return False, language, subs_file #standard output
    log( __name__ ," Login to Itasa failed. Check your username/password at the addon configuration.")

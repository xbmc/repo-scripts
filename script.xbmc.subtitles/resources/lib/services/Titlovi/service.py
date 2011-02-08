import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import toOpenSubtitles_two, log

main_url = "http://titlovi.com/titlovi/titlovi.aspx?"
debug_pretext = ""
subtitles_list = []

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
      <a class="naslovFl" href="http://titlovi.com/titlovi/house-m-d--101198/">HOUSE M D </a> <span class="godinaFl"> (2004) 1 CD Sezona6 Epizoda20</span><br />
      > 720p.WEB-DL.DD5.1.h.264-LP

      </td>
"""
subtitle_pattern = "<a class=\"naslovFl\" href=\"http://titlovi\.com/titlovi/[^\r\n\t]*?(\d{1,10})/\">([^\r\n\t]*?)</a> <span class=\"godinaFl\"> \(([12]\d{3})\) 1 CD (.{1,20})</span><br />\
(.{200,200})"
subinfo_pattern = "\r\n +> +(.*?)\r"

# multiple results pages:
# [ 13 ]</a> <a id="ctl00_ctl00_ctl00_contentholder_mainholder_subtitlesholder_hyp_14" href="http://titlovi.com/titlovi/titlovi.aspx?prijevod=lost&amp;jezik=&amp;stranica=14">14</a>
pages_pattern = "\[ \d{1,3} \]</a> <a id=\"ctl00_ctl00_ctl00_contentholder_mainholder_subtitlesholder_hyp_(\d{1,3})\""

#====================================================================================================================
# Functions
#====================================================================================================================

def to_titlovi_lang(language):
    if language == "Croatian":            return "hrvatski"
    elif language == "SerbianLatin":      return "srpski"
    elif language == "Cyrillic":          return "cirilica" # not a supported search language in addon settings
    elif language == "Slovenian":         return "slovenski"
    elif language == "BosnianLatin":      return "bosanski"
    elif language == "Macedonian":        return "makedonski"
    elif language == "English":           return "english"
    else:                                 return None

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    # this has to be last:
    s = s.replace("&amp;", "&")
    return s

def getallsubs(content, language, search_string, season, episode):
    i = 0
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        i = i + 1
        title_found = unescape(string.rstrip(matches.group(2)))
        log( __name__ , title_found )
        log( __name__ , search_string )
        if string.find(string.lower(title_found),string.lower(search_string)) > -1:
            subtitle_id    = matches.group(1)
            year_found     = matches.group(3)
            season_episode_found = string.rstrip(matches.group(4))
            filename = title_found
            languageshort = toOpenSubtitles_two(language)
            match = re.match(subinfo_pattern, matches.group(5), re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1)
                filename = filename + ' ' + description
            if len(season) > 0:
                season_episode = 'Sezona' + season + ' Epizoda' + episode
                if season_episode == season_episode_found:
                    subtitles_list.append({'rating': '0', 'sync': False, 'filename': filename, 'subtitle_id': subtitle_id, 'language_flag': 'flags/' + languageshort+ '.gif', 'language_name': language})
                    log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, subtitle_id))
            else:
                if len(season_episode_found) == 0:
                    subtitles_list.append({'rating': '0', 'sync': False, 'filename': filename, 'subtitle_id': subtitle_id, 'language_flag': 'flags/' + languageshort+ '.gif', 'language_name': language})
                    log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, subtitle_id))

def getnextpage(content):
    i = 0
    for matches in re.finditer(pages_pattern, content, re.IGNORECASE | re.DOTALL):
        i = i + 1
    if i == 1:
        return matches.group(1)
    else:
        return None

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = tvshow
    searchstring = searchstring.replace("The", "")
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    if to_titlovi_lang(lang1) is not None:
        url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik=" + to_titlovi_lang(lang1)
        content = geturl(url)
        if content is not None:
            getallsubs(content, lang1, searchstring, str(season), str(episode))
            nextpage = getnextpage(content)
            while nextpage is not None:
                url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik="  + to_titlovi_lang(lang1) + "&stranica=" + str(nextpage)
                content = geturl(url)
                getallsubs(content, lang1, searchstring, str(season), str(episode))
                nextpage = getnextpage(content)

    if (lang2 != lang1):
        if to_titlovi_lang(lang2) is not None:
            url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik=" + to_titlovi_lang(lang2)
            content = geturl(url)
            if content is not None:
                getallsubs(content, lang2, searchstring, str(season), str(episode))
                nextpage = getnextpage(content)
                while nextpage is not None:
                    url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik="  + to_titlovi_lang(lang2) + "&stranica=" + str(nextpage)
                    content = geturl(url)
                    getallsubs(content, lang2, searchstring, str(season), str(episode))
                    nextpage = getnextpage(content)

    if ((lang3 != lang2) and (lang3 != lang1)):
        if to_titlovi_lang(lang3) is not None:
            url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik=" + to_titlovi_lang(lang3)
            content = geturl(url)
            if content is not None:
                getallsubs(content, lang3, searchstring, str(season), str(episode))
                nextpage = getnextpage(content)
                while nextpage is not None:
                    url = main_url + "prijevod=" + urllib.quote(searchstring) + "&jezik="  + to_titlovi_lang(lang3) + "&stranica=" + str(nextpage)
                    content = geturl(url)
                    getallsubs(content, lang3, searchstring, str(season), str(episode))
                    nextpage = getnextpage(content)

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subtitle_id = subtitles_list[pos][ "subtitle_id" ]
    language = subtitles_list[pos][ "language_name" ]
    url = "http://titlovi.com/downloads/default.ashx?type=1&mediaid=" + str(subtitle_id)
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.srt") # assume unpacked subtitels file is an '.srt'
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

# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, urllib2
from utilities import log

_ = sys.modules[ "__main__" ].__language__

main_url = "http://ondertitel.com/"
debug_pretext = ""

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<strong><a href="/ondertitels/info/Avatar/48039.html" title="ondertitels Avatar" style="color: #000;">Avatar</a></strong> <img src="/images/nederlandse_vlag.jpg" height="15" width="20"> <a href="http://trailer-cinema.com/trailer/info/Avatar/Avatar.html" target="_blank"><img src="/images/icon_play-trailer.png" height="15" border="0"></a><br>
    			<font style="font-size: 11px; color: #444445;"><i>Avatar.RETAIL.DVDRip.XviD-DiAMOND</i></font>
				</div>
				</td>
				<td><a href="http://www.imdb.com/title/tt0499549/" target="_blank"><img src="/images/imdb_logo.gif" border="0"></a></td>

				<td style="width: 60px;">3 CD's</td><td><a href="/user_list.php?user=Goffini">Goffini</a></td></tr>
"""
subtitle_pattern = "<strong><a href=\"/(ondertitels/info/[^\n\r\t]*?.html)\"[^\n\r\t]*?>\
[\n\r\t ]*?<font style=\"font-size: 11px; color: #444445;\"><i>([^\r\n\t]*?)</i></font>[\n\r\t ]*?</div>[\n\r\t ]*?</td>\
[\n\r\t ]*?<td>[^\r\n\t]*?</td>[\r\n\t ]*?<td style=\"width: 60px;\">(\d) CD"
# group(1) = link to page with downloadlink, group(2) = filename, group(3) = number of CD's

# downloadlink pattern example:
"""
<a href="/getdownload.php?id=45071&userfile=94 Avatar (2009) PROPER TS XviD-MAXSPEED.zip"><b>Download</b></a>
"""
downloadlink_pattern = "<a href=\"/(getdownload\.php\?id=\d{1,10}&userfile=[^\n\r\t]*\.\w{3})\"><b>Download</b></a>"
# group(1) = downloadlink

#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(content, title, moviefile, subtitles_list, ):
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        if matches.group(3) == "1" and matches.group(2) <> "":
            link = matches.group(1)
            filename = matches.group(2)
            log( __name__ ,"%s Subtitles found: %s (link=%s)" % (debug_pretext, filename, link))
            if isexactmatch(filename, moviefile):
                subtitles_list.append({'rating': '0', 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': True, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})
            else:
                subtitles_list.append({'rating': '0', 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})


def isexactmatch(subsfile, moviefile):
    match = re.match("(.*)\.", moviefile)
    if match:
        moviefile = string.lower(match.group(1))
        subsfile = string.lower(subsfile)
        log( __name__ ," comparing subtitle file with moviefile to see if it is a match (sync):\nsubtitlesfile  = '%s'\nmoviefile      = '%s'" % (string.lower(subsfile), string.lower(moviefile)) )
        if string.lower(subsfile) == string.lower(moviefile):
            log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
            return True
        else:
            return False
    else:
        return False


def getdownloadlink(content):
    link = None
    i = 0
    for matches in re.finditer(downloadlink_pattern, content, re.IGNORECASE | re.DOTALL):
        link = matches.group(1)
        i = i + 1
    if i == 1:
        return link
    else:
         return None


def geturl(url):
    log( __name__ ,"%s Getting url:%s" % (debug_pretext, url))
    try:
        response   = urllib2.urlopen(url)
        content    = response.read()
        return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
        return_url = None
    return(content, return_url)


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    log( __name__ ,"%s Title = %s" % (debug_pretext, title))
    if len(tvshow) == 0: # only process movies
        url = main_url + "zoeken.php?type=1&trefwoord=" + urllib.quote_plus(title)
        Dutch = False
        if (string.lower(lang1) == "dutch") or (string.lower(lang2) == "dutch") or (string.lower(lang3) == "dutch"):
            Dutch = True
            content, response_url = geturl(url)
            if content is not None:
                log( __name__ ,"%s Getting subs ..." % debug_pretext)
                moviefile = os.path.basename(file_original_path)
                getallsubs(content, title, moviefile, subtitles_list)
        else:
            log( __name__ ,"%s Dutch language is not selected" % (debug_pretext))
            msg = "Won't work, Ondertitel is only for Dutch subtitles."
    else:
        log( __name__ ,"%s Tv show detected: %s" % (debug_pretext, tvshow))
        msg = "Won't work, Ondertitel is only for movies."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url = main_url + subtitles_list[pos][ "link" ]
    local_tmp_file = zip_subs
    content, response_url = geturl(url)
    downloadlink = getdownloadlink(content)
    if downloadlink is not None:
        try:
            url = main_url + downloadlink
            url = string.replace(url," ","+")
            log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
            content, response_url = geturl(url)
            if content is not None:
                log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
                local_file_handle = open(local_tmp_file, "w" + "b")
                local_file_handle.write(content)
                local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        language = subtitles_list[pos][ "language_name" ]
        return True, language, "" #standard output

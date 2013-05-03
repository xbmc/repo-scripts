# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, urllib2
from utilities import log

_ = sys.modules[ "__main__" ].__language__

main_url = "http://ondertitel.com/"
debug_pretext = ""
releases_types   = ['web-dl', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'aac20', 'hdtv', 'dvdrip', 'ac3', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<a href="/ondertitels/info/(500)-Days-of-Summer/44032.html" title="ondertitel (500) Days of Summer" style="color: #000;">(500) Days of Summer</a></strong> <img src="/images/nederlandse_vlag.jpg" height="11" width="18"></div> <div style="float:left;"><a href="http://www.imdb.com/title/tt1022603/" target="_blank"><img src="/images/imdb_logo.gif" border="0"></a> </div><br clear="both"></div>
							<div style="width: 490px; overflow:hidden; overflow:hidden"><font style="font-size: 11px; color: #444445;"><i>500.Days.of.Summer.2009.720p.BluRay.DTS.x264-WiKi</i></font><br></div>
"""
### Old pattern.
#subtitle_pattern = "<a href=\"(/ondertitels/info/[^/\n\r\t]+/\d+?\.html)\" title=\"[^/\n\r\t]+\" style=\"color: #000;\">[^\n\r\t]*?[\n\r\t]+\
#<div style=\"width: 490px; overflow:hidden; overflow:hidden\"><font style=\"font-size: 11px; color: #444445;\"><i>([^\n\r\t<]+?)</i></font><br></div>"

### HTML in the search results changed. This pattern fix it. ###
subtitle_pattern = "<a href=\"(/ondertitels/info/.+?.html)\" style=\"color: #161616;\">.+?[\r\n\t].+?<i>(.+?)</i></font></div>"
# group(1) = link, group(2) = filename


# downloadlink pattern example:
"""
<a href="/getdownload.php?id=45071&userfile=94 Avatar (2009) PROPER TS XviD-MAXSPEED.zip"><b>Download</b></a>
"""
downloadlink_pattern = "<a href=\"/(getdownload\.php\?id=\d{1,10}&userfile=[^\n\r\t]*\.\w{3})\"><b>Download</b></a>"
# group(1) = downloadlink

#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(content, title, moviefile, subtitles_list):
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        link = matches.group(1)
        filename = matches.group(2)
        log( __name__ ,"%s Subtitles found: %s (link=%s)" % (debug_pretext, filename, link))
        if isexactmatch(filename, moviefile):
            sync = True
            rating = 10
        else:
            rating = getrating(filename, moviefile)
            sync = False
            subtitles_list.append({'rating': str(rating), 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': sync, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})

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
                subtitles_list.sort(key=lambda x: [ x['sync'], x['rating']], reverse = True)
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

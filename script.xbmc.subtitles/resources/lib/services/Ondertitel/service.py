# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, urllib2
from utilities import log

_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.ondertitel.com/"
debug_pretext = ""

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<td onclick="location='http://www.ondertitel.com/ondertitels/info/Brooklyns-Finest/47638.html'" align=left><a href='http://www.ondertitel.com/ondertitels/info/Brooklyns-Finest/47638.html'><span class=window2 style="text-transform: capitalize">Brooklyn's Finest</span><br /> [Brooklyns.Finest.DVDSCREENER.XviD-MENTiON]</a></td>
"""
subtitle_pattern = "<td onclick=\"location=\'(http://www\.ondertitel\.com/ondertitels/info/[^\n\r\t]*?/\d{1,10}\.html)\'\" \
align=left><a href=\'http://www\.ondertitel\.com/ondertitels/info/[^\n\r\t]*?/\d{1,10}\.html\'><span class=window2 style=\"text-transform: capitalize\">\
([^\n\r\t]*?)</span><br />[ \[]{0,2}([^\n\r\t]*?)[\]]{0,1}</a></td>"
# group(1) = link to page with downloadlink, group(2) = title as found, group(3) = filename


# downloadlink pattern example:
"""
<a href="/getdownload.php?id=47638&userfile=7 Brooklyns.Finest.DVDSCREENER.XviD-MENTiON.zip"><b>Download</b></a>
"""
downloadlink_pattern = "<a href=\"/(getdownload\.php\?id=\d{1,10}&userfile=[^\n\r\t]*\.\w{3})\"><b>Download</b></a>"
# group(1) = downloadlink

#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(content, title, subtitles_list):
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        if matches.group(3) == "&nbsp;":
            filename = matches.group(2)
        else:
            filename = matches.group(3)
        link = matches.group(1)
        log( __name__ ,"%s Subtitles found: %s (link=%s)" % (debug_pretext, filename, link))
        subtitles_list.append({'rating': '0', 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})

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
        url = main_url + "?type=1+CD&p=zoek&trefwoord=" + urllib.quote_plus(title)
        Dutch = False
        if (string.lower(lang1) == "dutch") or (string.lower(lang2) == "dutch") or (string.lower(lang3) == "dutch"):
            Dutch = True
            content, response_url = geturl(url)
            if content is not None:
                log( __name__ ,"%s Getting subs ..." % debug_pretext)
                getallsubs(content, title, subtitles_list)
        else:
            log( __name__ ,"%s Dutch language is not selected" % (debug_pretext))
            msg = "Won't work, Ondertitel is only for Dutch subtitles."
    else:
        log( __name__ ,"%s Tv show detected: %s" % (debug_pretext, tvshow))
        msg = "Won't work, Ondertitel is only for movies."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url = subtitles_list[pos][ "link" ]
    local_tmp_file = zip_subs
    content, response_url = geturl(url)
    downloadlink = getdownloadlink(content)
    if downloadlink is not None:
        try:
            url = main_url + downloadlink
            url = string.replace(url," ","+")
            log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
            #response = urllib2.urlopen(url)
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

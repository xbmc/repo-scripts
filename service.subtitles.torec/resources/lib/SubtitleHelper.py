# -*- coding: utf-8 -*- 

import urllib
import codecs
import unicodedata

import xbmcaddon
import xbmc

import re
import os

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version')  # Module version
__scriptname__ = __addon__.getAddonInfo('name')

regexHelper = re.compile('\W+', re.UNICODE)

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)
    
def normalize_string(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')

def convert_to_utf(file):
    """
    Convert a file in cp1255 encoding to utf-8

    :param file: file to converted from CP1255 to UTF8
    """
    try:
        with codecs.open(file, "r", "cp1255") as f:
            srt_data = f.read()

        with codecs.open(file, 'w', 'utf-8') as output:
            output.write(srt_data)
    except UnicodeDecodeError:
        log(__name__, "got unicode decode error with reading subtitle data")

def check_and_parse_if_title_is_TVshow(manualTitle):
    try:
        manualTitle = manualTitle.replace("%20", " ")

        matchShow = re.search(r'(?i)^(.*?)\sS\d', manualTitle)
        if matchShow == None:
            return ["NotTVShow", "0", "0"]
        else:
            tempShow = matchShow.group(1)
        
        matchSnum = re.search(r'(?i)%s(.*?)E' %(tempShow+" s"), manualTitle)
        if matchSnum == None:
            return ["NotTVShow", "0", "0"]
        else:
            tempSnum = matchSnum.group(1)
        
        matchEnum = re.search(r'(?i)%s(.*?)$' %(tempShow+" s"+tempSnum+"e"), manualTitle)
        if matchEnum == None:
            return ["NotTVShow", "0", "0"]
        else:
            tempEnum = matchEnum.group(1)

        return [tempShow, tempSnum, tempEnum]

    except:
        return ["NotTVShow", "0", "0"]

def take_title_from_focused_item():
    labelMovieTitle = xbmc.getInfoLabel("ListItem.OriginalTitle")
    labelYear = xbmc.getInfoLabel("ListItem.Year")
    labelTVShowTitle = xbmc.getInfoLabel("ListItem.TVShowTitle")
    labelSeason = xbmc.getInfoLabel("ListItem.Season")
    labelEpisode = xbmc.getInfoLabel("ListItem.Episode")
    labelType = xbmc.getInfoLabel("ListItem.DBTYPE")  #movie/tvshow/season/episode
    isItMovie =  labelType == 'movie' or xbmc.getCondVisibility("Container.Content(movies)")
    isItEpisode = labelType == 'episode' or xbmc.getCondVisibility("Container.Content(episodes)")

    title = 'SearchFor...'
    if isItMovie and labelMovieTitle and labelYear:
        title = labelMovieTitle + " " + labelYear
    elif isItEpisode and labelTVShowTitle and labelSeason and labelEpisode:
        title = ("%s S%.2dE%.2d" % (labelTVShowTitle, int(labelSeason), int(labelEpisode))).replace(" ", "%20")

    return title

def parse_rls_title(item):
    title = regexHelper.sub(' ', item["title"])
    tvshow = regexHelper.sub(' ', item["tvshow"])

    groups = re.findall(r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})", title, re.I)

    if len(groups) == 0:
        groups = re.findall(r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})", tvshow, re.I)

    if len(groups) > 0 and len(groups[0]) >= 3:
        title, year, season, episode = groups[0]
        item["year"] = str(int(year)) if len(year) == 4 else year

        item["tvshow"] = regexHelper.sub(' ', title).strip()
        item["season"] = str(int(season))
        item["episode"] = str(int(episode))
        log(__name__, "TV Parsed Item: %s" % (item,))

    else:
        groups = re.findall(r"(.*?)(\d{4})", item["title"], re.I)
        if len(groups) > 0 and len(groups[0]) >= 1:
            title = groups[0][0]
            item["title"] = regexHelper.sub(' ', title).strip()
            item["year"] = groups[0][1] if len(groups[0]) == 2 else item["year"]

            log(__name__, "MOVIE Parsed Item: %s" % (item,))

def clean_title(item):
    title = os.path.splitext(os.path.basename(item["title"]))
    tvshow = os.path.splitext(os.path.basename(item["tvshow"]))

    if len(title) > 1:
        if re.match(r'^\.[a-z]{2,4}$', title[1], re.IGNORECASE):
            item["title"] = title[0]
        else:
            item["title"] = ''.join(title)
    else:
        item["title"] = title[0]

    if len(tvshow) > 1:
        if re.match(r'^\.[a-z]{2,4}$', tvshow[1], re.IGNORECASE):
            item["tvshow"] = tvshow[0]
        else:
            item["tvshow"] = ''.join(tvshow)
    else:
        item["tvshow"] = tvshow[0]

    item["title"] = unicode(item["title"], "utf-8")
    item["tvshow"] = unicode(item["tvshow"], "utf-8")
    # Removes country identifier at the end
    item["title"] = re.sub(r'\([^\)]+\)\W*$', '', item["title"]).strip()
    item["tvshow"] = re.sub(r'\([^\)]+\)\W*$', '', item["tvshow"]).strip()
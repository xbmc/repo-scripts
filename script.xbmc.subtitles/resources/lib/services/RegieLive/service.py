# -*- coding: UTF-8 -*-

#===============================================================================
# RegieLive.ro subtitles service.
# Version: 1.1
#
# Change log:
# 1.1 - Year is used for filtering (if available)
# 1.0 - First release.
#
# Created by: ThumbGen (2012)
#===============================================================================
import os, re, xbmc, xbmcgui, string, time, urllib2, cookielib
from utilities import log

BASE_URL = "http://subtitrari.regielive.ro/"
debug_pretext = ""
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11'
HOST = 'subtitrari.regielive.ro'
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

#===============================================================================
# Regular expression patterns
#===============================================================================

SEARCH_RESULTS_PATTERN = "An:</strong> (\d{4})<br/>.*?Subtitrari: </strong><a href=\"http://subtitrari\\.regielive\\.ro/([^/]+)/\""
SUBTITLE_LIST_PATTERN = 'subtitle_details left">[^<]+<a href="[^\"]+" class="b">(?P<title>[^<]+)</a> &nbsp;&nbsp;&nbsp;\[<a href="(?P<link>[^"]+)"  title="Download">Download</a>\]<br/>[^<]+<strong>Nr\. CD:</strong> (?P<cd>\d)(?P<opt>[^<]*<strong>Framerate:</strong>\s(?P<frame>[^\s]+) FPS)?.*?nota=\'(?P<rating>[\d\.]+)\' voturi'

TV_SEARCH_RESULTS_PATTERN = "An:</strong> (\d{4})<br/>.*?Subtitrari: </strong><a href=\"http://subtitrari\\.regielive\\.ro/([^/]+)/\""
TVSHOW_LIST_PATTERN_PREFIX = '</li>.*?<li class="subtitrare vers_\d+ ep_'
TVSHOW_LIST_PATTERN_SUFFIX = '">.*?<a href="[^"]+" class="download left" title="Download"></a>.*?<div class="subtitle_details left">[^<]+<a href="[^"]+" class="b">(?P<title>[^<]+)</a> &nbsp;&nbsp;&nbsp;\[<a href="(?P<link>[^"]+)"  title="Download">Download</a>\]<br/>(?P<opt2>[^<]+<strong>Nr\. CD:</strong> (?P<cd>\d))?(?P<opt>[^<]*<strong>Framerate:</strong>\s(?P<frame>[^\s]+) FPS)?.*?nota=\'(?P<rating>[\d\.]+)\' voturi'

#===============================================================================
# Private utility functions
#===============================================================================

# the function checks if the name of the subtitle is matching exactly the name of the video file
def isExactMatch(subsfile, videofile):
    match = re.match("(.*)\.", videofile)
    if match:
        videofile = string.lower(match.group(1))
        p = re.compile('(\s|\.|-)*cd\d(\s|\.|-)*', re.IGNORECASE)
        videofile = p.sub('', videofile)
        subsfile = string.lower(subsfile)
        if string.find(string.lower(subsfile),string.lower(videofile)) > -1:
            log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
            return True
        else:
            return False
    else:
        return False

# retrieves the content of the url (by using the specified referer in the headers)
def getURL(url, referer):
    #log( __name__ ,"Getting url: %s with referer %s" % (url, referer))
    opener.addheaders = [('User-agent', USER_AGENT),
                         ('Host', HOST),
                         ('Referer', referer)]
    content = None
    try:
        response = opener.open(url)
        content = response.read()
        response.close()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
    #log( __name__ ,"Got content from url: %s" % (url))
    return content
    
# returns the proper rating (converting the float rating from the website to the format accepted by the addon) 
def getFormattedRating(rating):
    return str(int(round(float(rating) * 2)))

# decide if the current subtitle is in sync
def isSync(title, file_original_path):
    return isExactMatch(title, os.path.basename(file_original_path))

def getReferer(pageId):
    return BASE_URL + pageId + '/'

def addSubtitle(subtitlesList, sync, title, link, referer, rating,cd):
    subtitlesList.append({'sync': sync,
                          'filename': title, 
                          'subtitle_id': link,
                          'referer': referer,
                          'rating':getFormattedRating(rating),
                          'language_flag': 'flags/ro.gif',
                          'language_name': cd + " CD",
                          'cd':cd})
    
# sort subtitlesList first by sync then by rating
def sortSubtitlesList(subtitlesList):
    # Bubble sort, to put syncs on top
    #for n in range(0,len(subtitlesList)):
        #for i in range(1, len(subtitlesList)):
         #   temp = subtitlesList[i]
            #if subtitlesList[i]["sync"] > subtitlesList[i-1]["sync"]:
                #subtitlesList[i] = subtitlesList[i-1]
                #subtitlesList[i-1] = temp
    if( len (subtitlesList) > 0 ):
        subtitlesList.sort(key=lambda x: [ x['sync'],getFormattedRating(x['rating'])], reverse = True)
    
# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(file_original_path, subtitlePageID, subtitlesList):
    referer = getReferer(subtitlePageID)
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + subtitlePageID, referer)
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(SUBTITLE_LIST_PATTERN, subtitlePage, re.IGNORECASE | re.DOTALL)
    #log( __name__ ,"found subtitles: %d" % (len(foundSubtitles)))
    for (title,link,cd,opt,frame,rating) in foundSubtitles:
        #log( __name__ ,"title:%s link: %s  cd: %s, rating: %s" % (title, link, cd, getFormattedRating(rating)))
        addSubtitle(subtitlesList, isSync(title, file_original_path), title, link, referer, rating, cd)

# Same as getAllSubtitles() but receives season and episode numbers and find them.
def getAllTVSubtitles(file_original_path, subtitlePageID, subtitlesList, season, episode):
    referer = getReferer(subtitlePageID)
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + subtitlePageID + "/sezonul-" + season + ".html", referer)
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(TVSHOW_LIST_PATTERN_PREFIX + episode + TVSHOW_LIST_PATTERN_SUFFIX, subtitlePage, re.IGNORECASE | re.DOTALL)
    #log( __name__ ,"found subtitles: %d" % (len(foundSubtitles)))
    for (title,link,opt2,cd,opt,frame,rating) in foundSubtitles:
        #log( __name__ ,"title:%s link: %s  cd: %s, rating: %s" % (title, link, cd, getFormattedRating(rating)))
        addSubtitle(subtitlesList, isSync(title, file_original_path), title, link, referer, rating, cd)

def isYearMatch(year, syear):
    return (year == syear) or str(year) == "" or str(syear) == "";

#===============================================================================
# Public interface functions
#===============================================================================

# This function is called when the service is selected through the subtitles
# addon OSD.
# file_original_path -> Original system path of the file playing
# title -> Title of the movie or episode name
# tvshow -> Name of a tv show. Empty if video isn't a tv show (as are season and
#           episode)
# year -> Year
# season -> Season number
# episode -> Episode number
# set_temp -> True iff video is http:// stream
# rar -> True iff video is inside a rar archive
# lang1, lang2, lang3 -> Languages selected by the user
def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitlesList = []
    msg = ""
    categ = '0'
    # Check if searching for tv show or movie and build the search string
    if tvshow:
        searchString = tvshow.replace(" ","+")
        #optimize query to get tvshows only
        categ = '2' 
    else:
        searchString = title.replace(" ","+")
        #optimize query to get movies only
        categ = '1'
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchString))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "cauta.html?s=" + searchString + "&categ=" + categ, 'subtitrari.regielive.ro')
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Didn't find any subs, please try again later."

    # When searching for episode 1 Sratim.co.il returns episode 1,10,11,12 etc'
    # so we need to catch with out pattern the episode and season numbers and
    # only retrieve subtitles from the right result pages.
    if tvshow:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.IGNORECASE | re.DOTALL)
        # Go over all the subtitle pages and add results to our list if season
        # and episode match
        for (syear, sid) in subtitleIDs:
            if(isYearMatch(year,syear)):
                getAllTVSubtitles(file_original_path,sid,subtitlesList,season,episode)
    else:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN, searchResults, re.IGNORECASE | re.DOTALL)
        # Go over all the subtitle pages and add results to our list
        for (syear,sid) in subtitleIDs:
            if(isYearMatch(year,syear)):
                getAllSubtitles(file_original_path,sid,subtitlesList)
    # sort the subtitles list first by sync then by rating
    sortSubtitlesList(subtitlesList)
    
    # Standard output -
    # subtitles list (list of tuples built in getAllSubtitles),
    # session id (e.g a cookie string, passed on to download_subtitles),
    # message to print back to the user
    return subtitlesList, "", msg

# This function is called when a specific subtitle from the list generated by
# search_subtitles() is selected in the subtitles addon OSD.
# subtitles_list -> Same list returned in search function
# pos -> The selected item's number in subtitles_list
# zip_subs -> Full path of zipsubs.zip located in tmp location, if automatic
# extraction is used (see return values for details)
# tmp_sub_dir -> Temp folder used for both automatic and manual extraction
# sub_folder -> Folder where the sub will be saved
# session_id -> Same session_id returned in search function
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subtitle_id = subtitles_list[pos][ "subtitle_id" ]
    language = subtitles_list[pos][ "language_name" ]
    referer = subtitles_list[pos][ "referer" ]
    url = BASE_URL + subtitle_id
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    # get the subtitles .zip
    content = getURL(url, referer)
    # write the subs archive in the temp location
    subs_file = os.path.join(tmp_sub_dir, "zipsubs.zip")
    try:
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, subs_file))
        local_file_handle = open(subs_file, "w" + "b")
        local_file_handle.write(content)
        local_file_handle.close()
    except:
        log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, subs_file))

    # Standard output -
    # True iff the file is packed as zip: addon will automatically unpack it.
    # language of subtitles,
    # Name of subtitles file if not packed (or if we unpacked it ourselves)
    return True, language, subs_file

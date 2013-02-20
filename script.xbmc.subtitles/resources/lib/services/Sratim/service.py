# -*- coding: UTF-8 -*-

#===============================================================================
# Sratim.co.il subtitles service.
# Version: 2.2
#
# Change log:
# 1.1 - Fixed bug with movie search: forgot to replace spaces with + signs.
# 1.2 - Better handling of search timeout (no results returned instead of error)
# 2.0 - Changed RE patterns and links to match new site layout (Thanks Shai Bentin!)
#       Fixed TV show subtitles (now navigates site to find requested episode)
# 2.1 - Changed RE patterns again due to layout change (Thanks BBLN for also suggesting different fix).
# 2.2 - Changed url to subtitle.co.il
# 2.3 - Added User Agent to getURL, fixed string related bugs and patterns
# 2.3.1 - stripped (year) from tvshow
#
# Created by: Ori Varon
# Changed by MeatHook (2.3)
#===============================================================================
import os, re, xbmc, xbmcgui, string, time, urllib2
from utilities import languageTranslate, log

BASE_URL = "http://www.subtitle.co.il/"
debug_pretext = ""

#===============================================================================
# Regular expression patterns
#===============================================================================

TV_SEARCH_RESULTS_PATTERN = "<a href=\"viewseries.php\?id=(\d+)[^>]*?title=.*?>"
SEARCH_RESULTS_PATTERN = "<a href=\"view.php\?id=(\d+)[^>]*?title=.*?>"
SUBTITLE_LIST_PATTERN = "downloadsubtitle\.php\?id=(?P<fid>\d*).*?subt_lang.*?title=\"(?P<language>.*?)\".*?subtitle_title.*?title=\"(?P<title>.*?)\""
TV_SEASON_PATTERN = "seasonlink_(?P<slink>\d+).*?>(?P<snum>\d+)</a>"
TV_EPISODE_PATTERN = "episodelink_(?P<elink>\d+).*?>(?P<enum>\d+)</a>"
USER_AGENT = "Mozilla%2F4.0%20(compatible%3B%20MSIE%207.0%3B%20Windows%20NT%206.0)"

#===============================================================================
# Private utility functions
#===============================================================================

# Returns the corresponding script language name for the Hebrew unicode language
def sratimToScript(language):
    languages = {
        "עברית"     : "Hebrew",
        "אנגלית"    : "English",
        "ערבית"     : "Arabic",
        "צרפתית"    : "French",
        "גרמנית"    : "German",
        "רוסית"     : "Russian",
        "טורקית"    : "Turkish",
        "ספרדית"    : "Spanish"
    }
    return languages[language]

# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):

    content = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_unredirected_header('User-Agent', USER_AGENT)
        response = urllib2.urlopen(req)        
        content = response.read()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
    return content

# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(subtitlePageID,languageList,subtitlesList):
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + "view.php?id=" + subtitlePageID + "&m=subtitles#")
    
    # Create a list of all subtitles found on page
    foundSubtitles = re.findall(SUBTITLE_LIST_PATTERN, subtitlePage)
    for (fid,language,title) in foundSubtitles:
        # Check if the subtitles found match one of our languages was selected
        # by the user
        if (sratimToScript(language) in languageList):
            subtitlesList.append({'rating': '0', 'sync': False,
                                  'filename': title, 'subtitle_id': fid,
                                  'language_flag': 'flags/' + \
                                  languageTranslate(sratimToScript(language),0,2) + \
                                  '.gif', 'language_name': sratimToScript(language)})

# Same as getAllSubtitles() but receives season and episode numbers and find them.
def getAllTVSubtitles(subtitlePageID,languageList,subtitlesList,season,episode):
    # Retrieve the subtitles page (html)
    subtitlePage = getURL(BASE_URL + "viewseries.php?id=" + subtitlePageID + "&m=subtitles#")
    # Retrieve the requested season
    foundSeasons = re.findall(TV_SEASON_PATTERN, subtitlePage)
    for (season_link,season_num) in foundSeasons:
        if (season_num == season):
            # Retrieve the requested episode
            subtitlePage = getURL(BASE_URL + "viewseries.php?id=" + subtitlePageID + "&m=subtitles&s="+str(season_link))
            foundEpisodes = re.findall(TV_EPISODE_PATTERN, subtitlePage)
            for (episode_link,episode_num) in foundEpisodes:
                if (episode_num == episode):
                    subtitlePage = getURL(BASE_URL + "viewseries.php?id=" + subtitlePageID + "&m=subtitles&s="+str(season_link)+"&e="+str(episode_link))
                    # Create a list of all subtitles found on page
                    foundSubtitles = re.findall(SUBTITLE_LIST_PATTERN, subtitlePage)
                    for (fid,language,title) in foundSubtitles:
                        # Check if the subtitles found match one of our languages was selected
                        # by the user
                        if (sratimToScript(language) in languageList):
                            subtitlesList.append({'rating': '0', 'sync': False,
                                                  'filename': title, 'subtitle_id': fid,
                                                  'language_flag': 'flags/' + \
                                                  languageTranslate(sratimToScript(language),0,2) + \
                                                  '.gif', 'language_name': sratimToScript(language)})


# Extracts the downloaded file and find a new sub/srt file to return.
# Note that Sratim.co.il currently isn't hosting subtitles in .txt format but
# is adding txt info files in their zips, hence not looking for txt.
# Based on Titlovi's service.py
def extractAndFindSub(tempSubDir,tempZipFile):
    # Remember the files currently in the folder and their number
    files = os.listdir(tempSubDir)
    init_filecount = len(files)
    filecount = init_filecount
    max_mtime = 0
    # Determine which is the newest subtitles file in tempSubDir
    for file in files:
        if (string.split(file,'.')[-1] in ['srt','sub']):
            mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
            if mtime > max_mtime:
                max_mtime =  mtime
    init_max_mtime = max_mtime
    # Wait 2 seconds so that the unpacked files are at least 1 second newer
    time.sleep(2)
    # Use XBMC's built-in extractor
    xbmc.executebuiltin("XBMC.Extract(" + tempZipFile + "," + tempSubDir +")")
    waittime  = 0
    while ((filecount == init_filecount) and (waittime < 20) and
           (init_max_mtime == max_mtime)): # Nothing extracted yet
        # Wait 1 second to let the builtin function 'XBMC.extract' unpack
        time.sleep(1)  
        files = os.listdir(tempSubDir)
        filecount = len(files)
        # Determine if there is a newer file created in tempSubDir
        # (indicates that the extraction had completed)
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
                mtime = os.stat(os.path.join(tempSubDir, file)).st_mtime
                if (mtime > max_mtime):
                    max_mtime =  mtime
        waittime  = waittime + 1
    if waittime == 20:
        log( __name__ ,"Failed to unpack subtitles in '%s'" % (tempSubDir))
        return ""
    else:
        log( __name__ ,"Unpacked files in '%s'" % (tempSubDir))        
        for file in files:
            # There could be more subtitle files in tempSubDir, so make sure we
            # get the newest subtitle file
            if ((string.split(file, '.')[-1] in ['srt', 'sub']) and
                (os.stat(os.path.join(tempSubDir, file)).st_mtime >
                 init_max_mtime)):
                log( __name__ ,"Unpacked subtitles file '%s'" % (file))        
                return os.path.join(tempSubDir, file)

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
    # List of user languages - easier to manipulate
    languageList = [lang1, lang2, lang3]
    msg = ""
 
    # Check if searching for tv show or movie and build the search string
    if tvshow:
        searchString = re.split(r'\s\(\d+\)$',tvshow)[0].replace(" ","+")
    else:
        searchString = title.replace(" ","+")
    	
    log( __name__ ,"%s Search string = *%s*" % (debug_pretext, title))
	
    # Retrieve the search results (html)

    searchResults = getURL(BASE_URL + "browse.php?q=" + searchString)
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Search timed out, please try again later."

    # When searching for episode 1 Sratim.co.il returns episode 1,10,11,12 etc'
    # so we need to catch with out pattern the episode and season numbers and
    # only retrieve subtitles from the right result pages.
    if tvshow:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,
                                 unicode(searchResults,"utf-8"))
        # Go over all the subtitle pages and add results to our list if season
        # and episode match
        for sid in subtitleIDs:
            getAllTVSubtitles(sid,languageList,subtitlesList,season,episode)
    else:
        # Find sratim's subtitle page IDs
        subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN, searchResults)
        # Go over all the subtitle pages and add results to our list
        for sid in subtitleIDs:
            getAllSubtitles(sid,languageList,subtitlesList)

    
    
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
    url = BASE_URL + "downloadsubtitle.php?id=" + subtitle_id
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    # Get the file content using geturl()
    content = getURL(url)
    if content:
        # Going to write them to standrad zip file (always zips in sratim)
        local_tmp_file = os.path.join(tmp_sub_dir, "zipsubs.zip")
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))

        # Extract the zip file and find the new sub/srt file
        subs_file = extractAndFindSub(tmp_sub_dir,local_tmp_file)
            
    # Standard output -
    # True iff the file is packed as zip: addon will automatically unpack it.
    # language of subtitles,
    # Name of subtitles file if not packed (or if we unpacked it ourselves)
    return False, language, subs_file

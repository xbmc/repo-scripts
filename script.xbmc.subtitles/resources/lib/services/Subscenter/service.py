# -*- coding: UTF-8 -*-

#===============================================================================
# Subscenter.org subtitles service.
# Version: 1.5.1
#
# TODO:
#  Filter title (The Office (US) => The Office)
# Change log:
# 1.1 - Fixed downloading of non-Hebrew subtitles.
# 1.2 - Added key field for download URL
# 1.3 - Fixed null values in website dictionary (changed to None)
# 1.4 - Fixed key field (Thanks ILRHAES)
# 1.5 - Added User Agent to getURL, fixed string related bugs and patterns
# 1.5.1 - Temp fix, TODO: Go over version 1.5 patterns.
#
# Created by: Ori Varon
# Changed by MeatHook (1.5)
# Version 1.5.1 by BBLN
#===============================================================================
import os, re, xbmc, xbmcgui, string, time, urllib2
from utilities import languageTranslate, log

BASE_URL = "http://www.subscenter.org"
USER_AGENT = "Mozilla%2F4.0%20(compatible%3B%20MSIE%207.0%3B%20Windows%20NT%206.0)"
debug_pretext = ""

#===============================================================================
# Regular expression patterns
#===============================================================================

MULTI_RESULTS_PAGE_PATTERN = u"עמוד (?P<curr_page>\d*) \( סך הכל: (?P<total_pages>\d*) \)"
SEARCH_RESULTS_PATTERN = "<div class=\"generalWindowRight\">.*?<a href=\"(?P<sid>.*?)\">"

#===============================================================================
# Private utility functions
#===============================================================================

# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):
    # Fix URLs with spaces in them

    url = url.replace(" ","%20")
    content = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_unredirected_header('User-Agent', USER_AGENT)
        response = urllib2.urlopen(req)        
        content = response.read()
    except:
        log( __name__ ,"Failed to get url: %s" % (url))
    # Second parameter is the filename
    return content

def getURLfilename(url):
    # Fix URLs with spaces in them

    url = url.replace(" ","%20")
    filename = None
    log( __name__ ,"Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_unredirected_header('User-Agent', USER_AGENT)
        response = urllib2.urlopen(req)        
        content = response.read()
        filename = response.headers['Content-Disposition']
        filename = filename[filename.index("filename="):]
    except:
        log( __name__ ,"Failed to get url: %s" % (url))
    # Second parameter is the filename
    return filename

# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(subtitlePageID,languageList,subtitlesList):
    log( __name__ ,"Get all subtitles")
    # Retrieve the subtitles page (html)
    try:
        subtitlePage = getURL(BASE_URL + str(subtitlePageID).lstrip())
    except:
        # Didn't find the page - no such episode?
        return
    # Didn't find the page - no such episode?
    if (not subtitlePage):
        return
    # Find subtitles dictionary declaration on page
    tempStart = subtitlePage.index("subtitles_groups = ")
    # Look for the following line break
    tempEnd = subtitlePage.index("\n",subtitlePage.index("subtitles_groups = "))
    toExec = "foundSubtitles = "+subtitlePage[tempStart+len("subtitles_groups = "):tempEnd]
    # Remove junk at the end of the line
    toExec = toExec[:toExec.rfind("}")+1]
    # Replace "null" with "None"
    toExec = toExec.replace("null","None")
    exec(toExec)
    log( __name__ ,"Built webpage dictionary")
    for language in foundSubtitles.keys():
        if (languageTranslate(language, 2, 0) in languageList): 
            for translator in foundSubtitles[language]:
                for quality in foundSubtitles[language][translator]:
                    for rating in foundSubtitles[language][translator][quality]:
                        subtitlesList.append({'rating': rating, 'sync': False,
                            'filename': foundSubtitles[language][translator][quality][rating]["subtitle_version"],
                            'subtitle_id': foundSubtitles[language][translator][quality][rating]["id"],
                            'language_flag': 'flags/' + language + '.gif',
                            'language_name': languageTranslate(language, 2, 0),
                            'key': foundSubtitles[language][translator][quality][rating]["key"]})

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

    # Check if tvshow and replace spaces with + in either case
    if tvshow:
        searchString = tvshow.replace(" ","+")
    else:
        searchString = title.replace(" ","+")

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchString.lower()))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Search timed out, please try again later."

    subtitleIDs = re.findall(SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
    log( __name__ , "Looking for page links")
    # Look for more subtitle pages
    pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
    # If we found them look inside for subtitles page links
    if (pages):
        for pageId in xrange(int(pages.group("total_pages"))):
            searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower() + "&page=" + str(pageId))
            tempSIDs = re.findall(SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
            for sid in tempSIDs:
                subtitleIDs.append(sid)
    # Uniqify the list
    subtitleIDs=list(set(subtitleIDs))
    # If looking for tvshows trying to append season and episode to url
    if tvshow:
        log( __name__ ,"%s Adding season and episode to urls" % (debug_pretext))
        for id in xrange(len(subtitleIDs)):
            subtitleIDs[id] += str("/"+season+"/"+episode+"/")
    for id in subtitleIDs:
        getAllSubtitles(id,languageList,subtitlesList)
    # Standard output
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
    filename = subtitles_list[pos][ "filename" ]
    key = subtitles_list[pos][ "key" ]
    url = BASE_URL + "/subtitle/download/"+languageTranslate(subtitles_list[pos][ "language_name" ], 0, 2)+"/"+str(subtitle_id)+"/?v="+filename+"&key="+key
    log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
    # Get the intended filename (don't know if it's zip or rar)
    archive_name = getURLfilename(url)
    # Get the file content using geturl()
    content = getURL(url)
    subs_file = None
    if content:
        local_tmp_file = os.path.join(tmp_sub_dir, archive_name)
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
    return False, subtitles_list[pos][ "language_name" ], subs_file

# -*- coding: UTF-8 -*-

#===============================================================================
# Subscenter.org subtitles service.
# Version: 2.5
#
# Change log:
# 1.1 - Fixed downloading of non-Hebrew subtitles.
# 1.2 - Added key field for download URL
# 1.3 - Fixed null values in website dictionary (changed to None)
# 1.4 - Fixed key field (Thanks ILRHAES)
# 1.5 - Added User Agent to getURL, fixed string related bugs and patterns
# 1.5.5 - Bug Fix for (1.5)
# 2.0 - Added rating algorithem 
#       Added supports downloading IDX\SUBS from sendspace.compile
#       Added sync icon added to files with rating>8
#       Added sorted subtitlelist by rating
# 2.0.1 - Bug fix
# 2.5 - support for Subscenter new website + workaround (10x to CaTz)
#
# Created by: Ori Varon
# Changed by: MeatHook (1.5)
# Changed by: Maor Tal 21/01/2014 (1.5.5, 2.0, 2.5)
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
MOVIES_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/movie/.*?)">.*?<div class="generalWindowBottom">'
TV_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/series/.*?)">.*?<div class="generalWindowBottom">'
releases_types   = ['2011','2009','2012','2010','2013','2014','web-dl', 'webrip', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'ac3', 'aac', 'hdtv', 'dvdscr' ,'dvdrip', 'ac3', 'brrip', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

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
    
def getrating(subsfile, videofile):
    x=0
    rating = 0
    log(__name__ ,"# Comparing Releases:\n %s [subtitle-rls] \n %s  [filename-rls]" % (subsfile,videofile))
    videofile = "".join(videofile.split('.')[:-1]).lower()
    subsfile = subsfile.lower().replace('.', '')
    videofile = videofile.replace('.', '')
    for release_type in releases_types:
        if (release_type in videofile):
            x+=1
            if (release_type in subsfile): rating += 1
    if(x): rating=(rating/float(x))*4
    # Compare group name
    if videofile.split('-')[-1] == subsfile.split('-')[-1] : rating += 1
    # Group name didnt match 
    # try to see if group name is in the beginning (less info on file less weight)
    elif videofile.split('-')[0] == subsfile.split('-')[-1] : rating += 0.5
    if rating > 0:
        rating = rating * 2
    log(__name__ ,"# Result is:  %f" % rating)
    return round(rating)
    
# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def getAllSubtitles(subtitlePageID,languageList,fname):
    # Retrieve the subtitles page (html)
    subs= []
    try:
        subtitlePage = getURL(BASE_URL + subtitlePageID)
    except:
        # Didn't find the page - no such episode?
        return
    # Didn't find the page - no such episode?
    if (not subtitlePage):
        return
    # Find subtitles dictionary declaration on page
    toExec = "foundSubtitles = " + subtitlePage
    # Remove junk at the end of the line
    toExec = toExec[:toExec.rfind("}")+1]
    # Replace "null" with "None"
    toExec = toExec.replace("null","None")
    exec(toExec) in globals(), locals()
    log( __name__ ,"Built webpage dictionary")
    for language in foundSubtitles.keys():
        if (languageTranslate(language, 2, 0) in languageList): 
            for translator in foundSubtitles[language]:
                for quality in foundSubtitles[language][translator]:
                    for rating in foundSubtitles[language][translator][quality]:
                        title=foundSubtitles[language][translator][quality][rating]["subtitle_version"]
                        Srating=getrating(title,fname)
                        subs.append({'rating': str(Srating), 'sync': Srating>=8,
                            'filename': title,
                            'subtitle_id': foundSubtitles[language][translator][quality][rating]["id"],
                            'language_flag': 'flags/' + language + '.gif',
                            'language_name': languageTranslate(language, 2, 0),
                            'key': foundSubtitles[language][translator][quality][rating]["key"],
                            'notes': re.search('http://www\.sendspace\.com/file/\w+$',foundSubtitles[language][translator][quality][rating]["notes"])})
    # sort, to put syncs on top
    return sorted(subs,key=lambda x: int(float(x['rating'])),reverse=True)

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
        searchString = re.split(r'\s\(\w+\)$',tvshow)[0].replace(" ","+")
    else:
        searchString = title.replace(" ","+")

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchString.lower()))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
    # Search most likely timed out, no results
    if (not searchResults):
        return subtitlesList, "", "Search timed out, please try again later."

    # Look for subtitles page links
    if tvshow:
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
    else:
        subtitleIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)    
    
    # Look for more subtitle pages
    pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
    # If we found them look inside for subtitles page links
    if (pages):
        while (not (int(pages.group("curr_page"))) == int(pages.group("total_pages"))):
            searchResults = getURL(BASE_URL + "/he/subtitle/search/?q="+searchString.lower()+"&page="+str(int(pages.group("curr_page"))+1))

            if tvshow:
                tempSIDs = re.findall(TV_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)
            else:
                tempSIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN,searchResults,re.DOTALL)



            for sid in tempSIDs:
                subtitleIDs.append(sid)
            pages = re.search(MULTI_RESULTS_PAGE_PATTERN,unicode(searchResults,"utf-8"))
    # Uniqify the list
    subtitleIDs=list(set(subtitleIDs))
    # If looking for tvshos try to append season and episode to url

    for i in range(len(subtitleIDs)):
        subtitleIDs[i] = subtitleIDs[i].replace("/subtitle/","/cinemast/data/")
        if (tvshow):
            subtitleIDs[i]=subtitleIDs[i].replace("/series/","/series/sb/")
            subtitleIDs[i] += season+"/"+episode+"/"
        else:
            subtitleIDs[i]=subtitleIDs[i].replace("/movie/","/movie/sb/")
             

    for sid in subtitleIDs:
        tmp = getAllSubtitles(sid,languageList,os.path.basename(file_original_path))
        subtitlesList=subtitlesList + ((tmp) if tmp else [])
    
    
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
    filename = subtitles_list[pos][ "filename" ]
    key = subtitles_list[pos][ "key" ]
    # check if need to download subtitle from sendspace
    if(subtitles_list[pos]["notes"]):
        # log to sendspace
        content = getURL(subtitles_list[pos]["notes"].group())
        # find download link
        url = re.search(r'<a id="download_button" href?="(.+sendspace.+\.\w\w\w)" ', content)
        content = None
        if (url):
            url = url.group(1)
            log( __name__ ,"%s Fetching subtitles from sendspace.com using url %s" % (debug_pretext, url))
            content = getURL(url)
            archive_name = "rarsubs" + re.search(r'\.\w\w\w$',url).group(0)
    else:
        url = BASE_URL + "/" + languageTranslate(subtitles_list[pos][ "language_name" ], 0, 2)+"/subtitle/download/"+languageTranslate(subtitles_list[pos][ "language_name" ], 0, 2)+"/"+str(subtitle_id)+"/?v="+filename+"&key="+key
        log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, url))
        # Get the intended filename (don't know if it's zip or rar)
        archive_name = getURLfilename(url)
        # Get the file content using geturl()
        content = getURL(url)
    subs_file = ""
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

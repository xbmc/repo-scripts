# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://swesub.nu/"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# direct link pattern example:
"""http://swesub.nu/title/tt0389722/"""
titleurl_pattern = 'http://swesub.nu/title/tt(\d{4,10})/'
# group(1) = movienumber

# find correct movie pattern example:
"""<h2><a href="/title/tt0389722/">30 Days of Night (2007)</a></h2>"""
title_pattern = '<h2><a href="/title/tt(\d{4,10})/">([^\r\n\t]*?) \((\d{4})\)</a></h2>'
# group(1) = movienumber, group(2) = title, group(3) = year

# videosubtitle pattern examples:
"""<a href="/download/25182/" rel="nofollow" class="dxs">I Am Number Four 2011 PPVRiP-IFLIX  (1 cd)</a>"""
"""<a href="/download/21581/" rel="nofollow" class="ssg">Avatar.2009.DVDRiP.XViD-iMBT (2 cd)</a>"""
videosubtitle_pattern = '<a href="/download/(\d{1,10})/"[^\n\r\t>]*?>([^\n\r\t]*?)\(1 cd\)</a>'
# group(1) = id, group(2) = filename

#====================================================================================================================
# Functions
#====================================================================================================================

def getallvideosubs(searchstring, file_original_path, movienumber, languageshort, languagelong, subtitles_list):
    url = main_url + 'title/tt' + str(movienumber) + '/'
    content, return_url = geturl(url)
    if content is not None:
        for matches in re.finditer(videosubtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            filename = string.strip(matches.group(2))
            if searchstring in filename:
                log( __name__ ,"Subtitles found: %s (id = %s)" % (filename, id))
                if isexactmatch(filename, os.path.basename(file_original_path)):
                    subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': True, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
                else:
                    subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})


def isexactmatch(subsfile, videofile):
    match = re.match("(.*)\.", videofile)
    if match:
        videofile = string.lower(match.group(1))
        subsfile = string.lower(subsfile)
        log( __name__ ," comparing subtitle file with videofile to see if it is a match (sync):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (string.lower(subsfile), string.lower(videofile)) )
        if string.find(string.lower(subsfile),string.lower(videofile)) > -1:
            log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (string.lower(subsfile)) )
            return True
        else:
            return False
    else:
        return False


def findtitlenumber(title, year):
    movienumber = None
    if year: # movie
        url = main_url + '/?s=' + urllib.quote_plus('%s (%s)' % (title, year))
    else: # tv show
        url = main_url + '/?s=' + urllib.quote_plus(title)
    content, return_url = geturl(url)
    if content is not None:
        match = re.search(titleurl_pattern, return_url, re.IGNORECASE | re.DOTALL)
        if match:
            movienumber = match.group(1)
        else:
            match = re.search(title_pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                if (string.lower(match.group(2)) == string.lower(title)):
                    movienumber = match.group(1)
    return movienumber


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"Getting url: %s" % (url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
        return_url = response.geturl()
    except:
        log( __name__ ,"Failed to get url:%s" % (url))
        content    = None
        return_url = None
    return content, return_url


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        movienumber = findtitlenumber(title, year)
        if movienumber is not None:
            log( __name__ ,"Movienumber found for: %s (%s)" % (title, year))
            getallvideosubs('', file_original_path, movienumber, "sv", "Swedish", subtitles_list)
        else:
            log( __name__ ,"Movienumber not found for: %s (%s)" % (title, year))
    if len(tvshow) > 0:
        movienumber = findtitlenumber(tvshow, None)
        if movienumber is not None:
            log( __name__ ,"Movienumber found for: %s (%s)" % (title, year))
            searchstring = "S%#02dE%#02d" % (int(season), int(episode))
            getallvideosubs(searchstring, file_original_path, movienumber, "sv", "Swedish", subtitles_list)
        else:
            log( __name__ ,"Movienumber not found for: %s (%s)" % (title, year))

#    log( __name__ ,"Search string = %s" % (searchstring))

#    swedish = 0
#    if string.lower(lang1) == "swedish": swedish = 1
#    elif string.lower(lang2) == "swedish": swedish = 2
#    elif string.lower(lang3) == "swedish": swedish = 3

#    if (swedish > 0):
#        getallsubs(searchstring, "sv", "Swedish", subtitles_list)

#    if (swedish == 0):
#        msg = "Won't work, Swesub.nu is only for Swedish subtitles."

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    url = main_url + "download/" + id + "/"
    log( __name__ ,"Fetching subtitles using url %s" % (url))
    content, return_url = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "swesub.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
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
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
            else:
                log( __name__ ,"Unpacked files in '%s'" % (tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"Unpacked subtitles file '%s'" % (file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

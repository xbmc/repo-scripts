# -*- coding: UTF-8 -*-

#===============================================================================
# Torec.net subtitles service.
# Version: 1.0
#
# Change log:
# 1.0 - First Release (02/11/2012)
#===============================================================================

import os, re, string, time, urllib2
from utilities import *
import xbmc

from TorecSubtitlesDownloader import TorecSubtitlesDownloader

__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    # Build an adequate string according to media type
    if tvshow:
        search_string = "%s S%02dE%02d" % (tvshow, int(season), int(episode))
    else:
        search_string = title
    
    subtitles_list = []
    msg = ""
    downloader = TorecSubtitlesDownloader()
    metadata = downloader.getSubtitleMetaData(search_string)
    if metadata != None:
        for option in metadata.options:
            subtitles_list.append({'page_id'       : metadata.id,
                                   'filename'      : option.name,
                                   'language_flag' : "flags/he.gif",
                                   'language_name' : "Hebrew",
                                   'subtitle_id'   : option.id,
                                   'sync'          : False,
                                   'rating'        : "0",
                                })

    return subtitles_list, "", msg

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    page_id                 = subtitles_list[pos]["page_id"]  
    subtitle_id             = subtitles_list[pos]["subtitle_id"]  

    icon =  os.path.join(__cwd__,"icon.png")
    delay = 20
    download_wait = delay
    downloader = TorecSubtitlesDownloader()
    # Wait the minimal time needed for retrieving the download link
    for i in range (int(download_wait)):
        downloadLink =  downloader.getDownloadLink(page_id, subtitle_id, False)
        if (downloadLink != None):
            break
        line2 = "download will start in %i seconds" % (delay,)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,icon))
        delay -= 1
        time.sleep(1)
        
    log(__name__ ,"Downloading subtitles from '%s'" % downloadLink)
    (subtitleData, subtitleName) = downloader.download(downloadLink)
    
    log(__name__ ,"Saving subtitles to '%s'" % zip_subs)
    downloader.saveData(zip_subs, subtitleData, False)
        
    return True,"Hebrew", "" #standard output
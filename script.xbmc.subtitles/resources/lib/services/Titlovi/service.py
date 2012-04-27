# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, xmlrpclib, base64
from xml.dom import minidom
from utilities import languageTranslate, log

KEY = "UGE4Qk0tYXNSMWEtYTJlaWZfUE9US1NFRC1WRUQtWA=="

def compare_columns(b,a):
  return cmp( b["language_name"], a["language_name"] ) 

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        content    = None
    return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    msg = ""
    subtitles_list = []
    search_url = "http://api.titlovi.com/xml_get_api.ashx?x-dev_api_id=%s&keyword=%s&uiculture=en"
    languages = [lang1, lang2, lang3]

    if len(tvshow) > 0:                                              # TvShow
        search_string = ("%s S%.2dE%.2d" % (tvshow,
                                            int(season), 
                                            int(episode),)
                                            ).replace(" ","+")      
    else:                                                            # Movie or not in Library
        if str(year) == "":                                          # Not in Library
            title, year = xbmc.getCleanMovieTitle( title )
        else:                                                        # Movie in Library
            year  = year
            title = title
        search_string = title.replace(" ","+")
    log( __name__ , "Search String [ %s ]" % (search_string,))
    subtitles = minidom.parseString(
                        geturl(search_url % (
                               base64.b64decode(KEY)[::-1], search_string))
                               ).getElementsByTagName("subtitle")
    if subtitles:
      url_base = "http://en.titlovi.com/downloads/default.ashx?type=1&mediaid=%s"
      for subtitle in subtitles:
        lang = subtitle.getElementsByTagName("language")[0].firstChild.data
        if lang == "rs": lang = "sr"
        if lang == "ba": lang = "bs"
        if lang == "si": lang = "sl"
        lang_full = languageTranslate(lang, 2,0)
        if lang_full in languages:
            sub_id = subtitle.getElementsByTagName("url")[0].firstChild.data
            movie = subtitle.getElementsByTagName("safeTitle")[0].firstChild.data
            if subtitle.getElementsByTagName("release")[0].firstChild:
                filename = "%s - %s" % (movie, subtitle.getElementsByTagName("release")[0].firstChild.data)
            else:
                filename = movie  
            rating = int(float(subtitle.getElementsByTagName("score")[0].firstChild.data)*2)
            flag_image = "flags/%s.gif" % lang
            link = url_base % sub_id.split("-")[-1].replace("/","")            
            subtitles_list.append({'filename'     :filename,
                                   'link'         :link,
                                   'language_name':lang_full,
                                   'language_id'  :lang,
                                   'language_flag':flag_image,
                                   'movie'        :movie,
                                   'rating'       :str(rating),
                                   'sync'         :False
                                   })

    subtitles_list = sorted(subtitles_list, compare_columns)
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    language = subtitles_list[pos][ "language_name" ]
    url = subtitles_list[pos][ "link" ]
    log( __name__ ,"Fetching subtitles using url %s" % url)
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "titlovi.srt") # assume unpacked subtitels file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % local_tmp_file)
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % local_tmp_file)
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
            while ((filecount == init_filecount) and
                   (waittime < 20) and
                   (init_max_mtime == max_mtime)): # nothing yet extracted
                time.sleep(1) # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file 
                # created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"Failed to unpack subtitles in '%s'" % tmp_sub_dir)
            else:
                log( __name__ ,"Unpacked files in '%s'" % tmp_sub_dir)
                for file in files:
                    # there could be more subtitle files 
                    #in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if ((string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and 
                        (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime)): 
                        # unpacked file is a newly created subtitle file
                        log( __name__ ,"Unpacked subtitles file '%s'" % file)
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output
        
       

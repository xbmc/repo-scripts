# coding=iso-8859-2
import sys
import os
import os.path
import string
import urllib
import urllib2
import re
import time
import subutils
import subenv
from utilities import *

_ = sys.modules[ "__main__" ].__language__

base_urls = ["http://feliratok.info/"]
search_url_postfix = "?nyelv=&searchB=Mehet&search="

subtitle_pattern =                    '<tr[^>]*>\s*'
subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</table>\s*</td>\s*' # picture
subtitle_pattern = subtitle_pattern +    '<td[^>]*>\s*<small>(?P<lang>.*?)</small>\s*</td>\s*' # language
subtitle_pattern = subtitle_pattern +    '<td[^>]*onclick="adatlapnyitas\(\'(?P<id>[a-zA-Z_0-9]*)\'\)"[^>]*>\s*'   # onclick="adatlapnyitas\(\'(?P<id>[0-9]*?)\'\)"[^>]*
subtitle_pattern = subtitle_pattern +      '<div[^>]*>(?P<huntitle>.*?)</div>\s*' # hungarian title
subtitle_pattern = subtitle_pattern +      '<div[^>]*>(?P<origtitle>.*?)</div>\s*' # original title
subtitle_pattern = subtitle_pattern +    '</td>\s*'
subtitle_pattern = subtitle_pattern +    '<td[^>]*>(?P<uploader>.*?)</td>\s*' # uploader
subtitle_pattern = subtitle_pattern +    '<td[^>]*>(?P<date>.*?)</td>\s*' # date
subtitle_pattern = subtitle_pattern +    '<td[^>]*>\s*<a href="(?P<link1>.*?fnev=)(?P<link2>[^&"]*)(?P<link3>&[^"]*)?">.*?</a>\s*</td>\s*' # download link
subtitle_pattern = subtitle_pattern +  '</tr>'

#subtitle_pattern =                    '<tr[^>]*>\s*'
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # picture
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # language
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # titles
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # uploader
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # date
# subtitle_pattern = subtitle_pattern +    '<td[^>]*>.*?</td>\s*' # download link
#subtitle_pattern = subtitle_pattern +  '</tr>'



def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): 
#input:
#   title: if it's a tv show episode and it's in the library, then it's the title of the _episode_,
#          if it's a tv show episode and it is not in the library, then it's the cleaned up name of the file,
#          if it's a movie and it's in the library, then it's the title of the movie (as stored in the lib.),
#          otherwise it's the title of the movie deduced from the filename
#   tvshow: the title of the tv show (if it's a tv show, of cource) as stored in the library or deduced from the filename
#   year: if the movie is not in the library, it's emtpy
#   set_temp: (boolean) indicates if the movie is at some place where you can't write (typically: if it's accessed via http)
#   rar: (boolean) indicates if the movie is in a rar archive
#output: (result, session_id, message)
#   result: the list of subtitles
#   session_id: this string is given to the download_subtitles function in the session_id parameter
#   message: if it's not empty, then this message will be shown in the search dialog box instead of the title/filename

    subenv.debuglog("INPUT:: path: %s, title: %s, tvshow: %s, year: %s, season: %s, episode: %s, set_temp: %s, rar: %s, lang1: %s, lang2: %s, lang3: %s" % (file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3))
    
    msg = ""
    subtitles_list = []  
    if len(tvshow) > 0:                                              # TvShow
        search_string = tvshow                                       # ("%s - %dx%.2d" % (tvshow, int(season), int(episode)))
        full_filename = os.path.basename(file_original_path)
    else:                                                            # if not in Library: year == ""
        full_filename = os.path.basename(os.path.dirname(file_original_path)) + ".avi"
        if title == "": title, year = subenv.clean_title( file_original_path ) 
        search_string = title
    
    # remove year from the end of the search string [eg.: foo (2010) ], could happen with certain tv shows (e.g. Castle(2009), V (2009), etc.)
    m2 = re.findall("\(?\d{4}\)?$", search_string)
    if len(m2) > 0 :
        m2len = -len(m2[0])
        search_string = search_string[:m2len]

    search_string = search_string.strip()
    if (len(search_string) == 1): search_string = search_string + " "
    subenv.debuglog( "Search String [ %s ]" % ( search_string, ) )     
    
    subtitles_list = []
    try:
        base_url = base_urls[0]
        url = base_url + search_url_postfix + urllib.quote_plus(search_string)
        content = ""
        subenv.debuglog("Getting url: %s" % (url) )
        content = urllib2.urlopen(url).read()

        #type of source
        patterntype = r'.+?\W(720p|1080p|1080|720|dvdscr|brrip|bdrip|dvdrip|hdtv|PPVRip|TS|R5|WEB\-DL)\W.+'
        matchtype = re.search(patterntype, full_filename,  re.I)
        release_type = ""
        if matchtype: release_type = matchtype.group(1).lower()
        
        #releaser
        releaser = ""
        patternreleaser = r'.+\-(\w+?)(\.\[\w+\])?\.\w{3}$'
        matchreleaser = re.search(patternreleaser, full_filename,  re.I)
        if matchreleaser: releaser = matchreleaser.group(1).lower()
        
        #on feliratok.info the episode number is listed with a leading zero (if below 10), e.g.: 4x02
        sep = season + "x" + str(episode).zfill(2)
        subenv.debuglog("Release type: %s, Releaser: %s, Episode str: %s" % (release_type, releaser, sep) )
        
        html_encoding = 'utf8'
        decode_policy = 'replace'

        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):  #  | re.UNICODE
            #subenv.debuglog("Found a movie on search page")
            link = (matches.group('link1') + urllib.quote_plus(matches.group('link2')) + matches.group('link3')).decode(html_encoding, decode_policy)
            hun_title = matches.group('huntitle').decode(html_encoding, decode_policy)
            orig_title = matches.group('origtitle').decode(html_encoding, decode_policy)
            hun_langname = matches.group('lang').decode(html_encoding, decode_policy)
            sub_id = matches.group('id').decode(html_encoding, decode_policy)
            #subenv.debuglog("Found movie on search page: orig_title: %s, hun: %s, lang: %s, link: %s, subid: %s" % (orig_title, hun_title, hun_langname, link, sub_id) )
            
            hun_title, parenthesized =subutils.remove_parenthesized_parts(hun_title)
            orig_title = orig_title + parenthesized
            
            eng_langname = subutils.lang_hun2eng(hun_langname)
            flag = languageTranslate(eng_langname,0,2)
            if flag == "": flag = "-"

            score = 0
            rating = 0

            
            orig_title_low = orig_title.lower()
            search_low = search_string.lower()
            if (release_type != "") and (release_type in orig_title_low): 
                score += 10
                rating += 1
            if (releaser != "") and (releaser in orig_title_low): 
                score += 5
                rating += 1
            if (year != "") and (str(year) in orig_title_low):
                score += 20
            if (orig_title_low.startswith(search_low) or hun_title.startswith(search_low)):
                score += 500
                rating += 4


            if hun_langname.lower() == "magyar": score += 1
                
            if len(tvshow) > 0:
                if sep in orig_title_low: 
                    score += 100
                    rating += 4
            else:
                rating *= 1.25

            sync = (rating == 10)
            #rating format must be string 
            rating = str(int(rating))
            
            subenv.debuglog("Found movie on search page: orig_title: %s, hun: %s, lang: %s, link: %s, flag: %s, rating: %s, score: %s" % (orig_title, hun_title, hun_langname, link, flag, rating, score) )
            subtitles_list.append({'movie':  orig_title, 'filename': orig_title + " / " + hun_title, 'link': link, 'id': sub_id, 'language_flag': 'flags/' + flag + '.gif', 'language_name': eng_langname, 'movie_file':file_original_path, 'eng_language_name': eng_langname, 'sync': sync, 'rating': rating, 'format': 'srt', 'base_url' : base_url, 'score': score })

        subenv.debuglog("%d subtitles found" % (len(subtitles_list)) )
        error_msg = ""
        if len(subtitles_list) == 0: 
            error_msg = "No subtitles found"
        else:
            #subtitles_list = sorted(subtitles_list,key=lambda subtitle: subtitle['language_name'], reverse=True);
            subtitles_list = sorted(subtitles_list,key=lambda sub: sub['score'], reverse=True);
            
        return subtitles_list, "", error_msg #standard output

    except Exception, inst: 
        subenv.errorlog( "query error: %s" % (inst))
        msg = "Query error:" + str(inst)
        subtitles_list = []
        return subtitles_list, "", msg #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): 
#input:
#   subtitles_list[pos]: is the selected subtitle data record (as was returned by search_subtitles())
#   zip_subs: see 'zipped' output parameter
#   tmp_sub_dir: a tmp dir that should be used to download the subtitle into
#   sub_folder: the dir where the subtitle will be automatically copied by the caller
#   session_id: the session_id string returned by search_subtitles()
#output: (zipped, language, subtitles_file)
#   zipped: (boolean) if it's true, then the output subtitle is zippped and is in the file 
#           given by the 'zip_subs' input parameter, and the 'subtitles_file' return value is discarded
#   language: the language of the subtitle (the full english name of the language)
#   subtitles_file: if zipped is false, then this gives the full path of the downloaded subtitle file
    subs_file = ""
    try:
        import urllib
        subdata = subtitles_list[pos]
        language = subdata["eng_language_name"]
        if language == "": language = "Hungarian"
        base_url = subdata["base_url"]

        #subenv.debuglog("INPUT:: subtitles_data: %s, pos: %s, zip_subs: %s, tmp_sub_dir: %s, sub_folder: %s, session_id: %s" % (subdata, pos, zip_subs, tmp_sub_dir, sub_folder, session_id) )

        # ##########################################################################################################
        # download subtitle file
        
        url = base_url + subdata[ "link" ]
        subenv.debuglog( "download link: %s" % (url,) ) 
        
        f = urllib.urlopen(url)
        response = urllib.urlopen(url)

        
        # find out the sub filename
        disp_header = response.info().getheader("Content-Disposition", "");
        m1 = re.findall('filename="([^"]+)"', disp_header, re.IGNORECASE);
        if len(m1) > 0:
            local_tmp_filename = m1[0].replace("\\", "").replace("/", "_")
        else:
            local_tmp_filename = "SuperSubtitles.srt"

        # parse downloaded file format
        ext_idx = local_tmp_filename.rfind(".")
        if (ext_idx >= 0):
            format = local_tmp_filename[ext_idx + 1:]
        else:
            format = "srt"
        subenv.debuglog("Downloaded file format: %s, filename: %s" % (format, local_tmp_filename) )

        # download file    
        local_tmp_path = os.path.join(tmp_sub_dir, "SuperSubtitles." + format)
        try:
            subenv.debuglog("Saving file to: %s" % (local_tmp_path) )
            local_file_handle = open(local_tmp_path, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            subenv.debuglog("Failed to save file to '%s'" % (local_tmp_path) )
            return False, language, subs_file #standard output
        else:
            subenv.debuglog("file saved to '%s'" % (local_tmp_path) )
        

        # unpack if needed
        if (format != "zip") and (format != "rar"):
            subs_file = local_tmp_path
            packed = False
        else:
            packed = True
            
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            filecount = init_filecount
            subenv.unpack_archive(local_tmp_path, tmp_sub_dir)
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 5): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                waittime  = waittime + 1
            if waittime == 5:
                subenv.debuglog("Failed to unpack subtitles files into '%s'" % (tmp_sub_dir) )
            else:
                subenv.debuglog("Unpacked files in '%s'" % (tmp_sub_dir) )
                unpacked_subs = []
                for file in files:
                    if (string.split(file, '.')[-1] in ["srt", "sub", "txt", "ssa", "smi"]):
                        unpacked_subs.append(file)
                        
                if len(unpacked_subs) == 0: return False, language, ""
                
                subs_file = ""
                movie = subdata['movie_file']
                for sub in unpacked_subs:
                    if subutils.filename_match_exact(movie, sub):
                        subs_file = sub
                        subenv.debuglog("Exact match found" )
                        break
                        
                if subs_file == "":
                    for sub in unpacked_subs:
                        if subutils.filename_match_tvshow(movie, sub):
                            subs_file = sub
                            subenv.debuglog("tv show match found" )
                            break

                if subs_file == "": subs_file = unpacked_subs[0]
                subs_file = os.path.join(tmp_sub_dir, subs_file)
                subenv.debuglog("Unpacked subtitles file selected: '%s'" % (subs_file) )
        return False, language, subs_file #standard output

    except Exception, inst: 
        subenv.errorlog( "download error : %s" % (inst))
        return False, language, subs_file #standard output
    
    
    

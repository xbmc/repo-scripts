# -*- coding: UTF-8 -*-
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import shutil

from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.subtitles.gr"
debug_pretext = "subtitles.gr"

def get_url(url,referer=None):
    if referer is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'}
    else:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 'Referer' : referer}
    req = urllib2.Request(url,None,headers)
    response = urllib2.urlopen(req)
    content = response.read()
    response.close()
    content = content.replace('\n','')
    return content

def get_rating(downloads):
    rating = int(downloads)
    if (rating < 50):
        rating = 1
    elif (rating >= 50 and rating < 100):
        rating = 2
    elif (rating >= 100 and rating < 150):
        rating = 3
    elif (rating >= 150 and rating < 200):
        rating = 4
    elif (rating >= 200 and rating < 250):
        rating = 5
    elif (rating >= 250 and rating < 300):
        rating = 6
    elif (rating >= 300 and rating < 350):
        rating = 7
    elif (rating >= 350 and rating < 400):
        rating = 8
    elif (rating >= 400 and rating < 450):
        rating = 9
    elif (rating >= 450):
        rating = 10
    return rating

def unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder):
    subs_file = ""
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
        log( __name__ ," Failed to unpack subtitles in '%s'" % (tmp_sub_dir))
        pass
    else:
        log( __name__ ," Unpacked files in '%s'" % (tmp_sub_dir))
        pass
        for file in files:
            # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
            if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                log( __name__ ," Unpacked subtitles file '%s'" % (file))
                subs_file = os.path.join(tmp_sub_dir, file)
    return subs_file

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
    subtitles_list = []
    msg = ""

    if not (string.lower(lang1) or string.lower(lang2) or string.lower(lang3)) == "greek":
        msg = "Won't work, subtitles.gr is only for Greek subtitles."
        return subtitles_list, "", msg #standard output

    try:
        log( __name__ ,"%s Clean title = %s" % (debug_pretext, title))
        premiered = year
        title, year = xbmc.getCleanMovieTitle( title )
    except:
        pass

    if len(tvshow) == 0: # Movie
        searchstring = "%s (%s)" % (title, premiered)
    elif len(tvshow) > 0 and title == tvshow: # Movie not in Library
        searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
    elif len(tvshow) > 0: # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    else:
        searchstring = title

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))
    get_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    return subtitles_list, "", msg #standard output

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ""
    language = subtitles_list[pos][ "language_name" ]
    name = subtitles_list[pos][ "filename" ]
    id = subtitles_list[pos][ "id" ]
    id = re.compile('(.+?.+?)/').findall(id)[-1]
    id = 'http://www.findsubtitles.eu/getp.php?id=%s' % (id)

    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, id))
        response = urllib.urlopen(id)
        content = response.read()
        type = content[:4]
    except:
        log( __name__ ,"%s Failed to parse url:%s" % (debug_pretext, id))
        return True,language, "" #standard output

    if type == 'Rar!':
        local_tmp_file = os.path.join(tmp_sub_dir, "subtitlesgr.rar")
    elif type == 'PK':
        local_tmp_file = os.path.join(tmp_sub_dir, "subtitlesgr.zip")
    else:
        log( __name__ ,"%s Failed to get correct content type" % (debug_pretext))
        return True,language, "" #standard output

    try:
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(content)
        local_file_handle.close()

        log( __name__ ,"%s Extracting temp subtitles" % (debug_pretext))
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
        time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack

        log( __name__ ,"%s Cleaning temp directory:%s" % (debug_pretext, tmp_sub_dir))
        files = os.listdir(tmp_sub_dir)
        try:
            for file in files:
                file = os.path.join(tmp_sub_dir, file)
                os.remove(file)
        except:
            pass

        log( __name__ ,"%s Getting subtitles from extracted directory" % (debug_pretext))
        tmp_sub_extract_dir = os.path.join(tmp_sub_dir, "subs")
        files = os.listdir(tmp_sub_extract_dir)
        for file in files:
            local_tmp_extract_file = os.path.join(tmp_sub_extract_dir, file)
            local_tmp_file = os.path.join(tmp_sub_dir, file)
            if (file.endswith('.rar') or file.endswith('.zip')):
                shutil.copy(local_tmp_extract_file, tmp_sub_dir)
                subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
            elif (file.endswith('.srt') or file.endswith('.sub')):
                shutil.copy(local_tmp_extract_file, tmp_sub_dir)
                subs_file = local_tmp_file
    except:
        log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        pass

    return False, language, subs_file #standard output

def get_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search.php?name=%s&sort=downloads+desc' % (main_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=main_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(<img src=.+?flags/el.gif.+?</tr>)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('title = "(.+?)"').findall(subtitle)[0]
            filename = filename.split("subtitles for")[-1]
            filename = filename.strip()
            id = re.compile('href="(.+?)"').findall(subtitle)[0]
            try:
                uploader = re.compile('class="link_from">(.+?)</a>').findall(subtitle)[0]
                uploader = uploader.strip()
                if uploader == 'movieplace': uploader = 'GreekSubtitles'
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('class="latest_downloads">(.+?)</td>').findall(subtitle)[0]
                downloads = re.sub("\D", "", downloads)
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            if not (uploader == 'Εργαστήρι Υποτίτλων' or uploader == 'subs4series'):
                log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
                subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

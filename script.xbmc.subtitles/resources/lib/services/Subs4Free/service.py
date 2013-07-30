# -*- coding: UTF-8 -*-
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import mechanize
from utilities import log
_ = sys.modules[ "__main__" ].__language__

movie_url = "http://www.small-industry.com"
tvshow_url = "http://www.subs4series.com"
debug_pretext = "subs4free"

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
    while (filecount == init_filecount) and (waittime < 10) and (init_max_mtime == max_mtime): # nothing yet extracted
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
    if waittime == 10:
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
        msg = "Won't work, subs4free is only for Greek subtitles."
        return subtitles_list, "", msg #standard output

    try:
        log( __name__ ,"%s Clean title = %s" % (debug_pretext, title))
        premiered = year
        title, year = xbmc.getCleanMovieTitle( title )
    except:
        pass

    content = 1
    if len(tvshow) == 0: # Movie
        searchstring = "%s (%s)" % (title, premiered)
    elif len(tvshow) > 0 and title == tvshow: # Movie not in Library
        searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
    elif len(tvshow) > 0: # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        content = 2
    else:
        searchstring = title

    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))
    if content == 1:
        get_movie_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    else:
        get_tvshow_subtitles_list(searchstring, "el", "Greek", subtitles_list)
    return subtitles_list, "", msg #standard output

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ""
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    name = subtitles_list[pos][ "filename" ]
    name = name.replace('.',' ')

    # Browser
    browser = mechanize.Browser()
    browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0')]
    browser.addheaders = [('Referer', id)]

    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, id))
        response = browser.open(id)
        content = response.read()
        log( __name__ ,"%s Getting subtitle link" % (debug_pretext))
        try:
            subtitle_id = re.compile('href="(getSub-.+?)"').findall(content.replace('\n',''))[1] # movie_url
        except:
            pass
        try:
            subtitle_id = re.compile('href="(/getSub-.+?)"').findall(content.replace('\n',''))[1] # tvshow_url
        except:
            pass
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, subtitle_id))
        response = browser.open(subtitle_id)
        content = response.read()
        type = response.info()["Content-type"]
    except:
        log( __name__ ,"%s Failed to parse url:%s" % (debug_pretext, id))
        return False, language, subs_file #standard output

    if type == 'application/x-rar-compressed':
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.rar")
        redirect = False
        packed = True
    elif type == 'application/zip':
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.zip")
        redirect = False
        packed = True
    elif not type.startswith('text/html'):
        local_tmp_file = os.path.join(tmp_sub_dir, "subs4series.srt") # assume unpacked subtitels file is an '.srt'
        subs_file = local_tmp_file
        redirect = False
        packed = False
    else:
        redirect = True

    if redirect is False:
        try:
            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
            if packed:
                subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
            pass
    else:
        try:
            log( __name__ ,"%s Getting subtitles by subz.tv" % (debug_pretext))
            subtitles = re.compile("(<li style='margin-bottom.+?</li>)").findall(content.replace('\n',''))
            for subtitle in subtitles:
                try:
                    try:
                        subz = re.compile("<span.+?>(.+?)</span>.+?</b>").findall(subtitle)[0]
                        subz = subz.replace('.',' ')
                    except:
                        subz = ''
                        pass
                    id = re.compile("<a href='(.+?)'").findall(subtitle)[0]
                    id = id.replace('amp;','')
                    id = 'http://www.subz.tv/infusions/pro_download_panel/%s&dlok=on' % (id)
                    if re.search(subz,name) is not None:
                        response = browser.open(id)
                        content = response.read()
                        try:
                            local_tmp_file = os.path.join(tmp_sub_dir, "subztv.rar")
                            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
                            local_file_handle = open(local_tmp_file, "wb")
                            local_file_handle.write(content)
                            local_file_handle.close()
                            subs_file = unpack_subtitles(local_tmp_file, zip_subs, tmp_sub_dir, sub_folder)
                            if subs_file == "":
                                local_tmp_file2 = os.path.join(tmp_sub_dir, "subztv.srt")
                                os.rename(local_tmp_file, local_tmp_file2)
                                subs_file = local_tmp_file2
                        except:
                            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
                            pass
                        break
                except:
                    pass
        except:
            log( __name__ ,"%s Failed to get subtitles by subz.tv" % (debug_pretext))
            pass

    return False, language, subs_file #standard output

def get_movie_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search_report.php?search=%s&x=14&y=11&searchType=1' % (movie_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=movie_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(/el.gif" alt="Greek".+?</B>DLs)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('<B>(.+?)</B>').findall(subtitle)[0]
            id = re.compile('href="link.php[?]p=(.+?)"').findall(subtitle)[0]
            id = '%s/%s' % (movie_url, id)
            try:
                uploader = re.compile('<B>(.+?)</B>').findall(subtitle)[1]
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('<B>(.+?)</B>').findall(subtitle)[-1]
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

def get_tvshow_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    url = '%s/search_report.php?search=%s&x=14&y=11&searchType=1' % (tvshow_url, urllib.quote_plus(searchstring))
    try:
        log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
        content = get_url(url,referer=tvshow_url)
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        return
    try:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        subtitles = re.compile('(/el.gif" alt="Greek".+?</B>DLs)').findall(content)
    except:
        log( __name__ ,"%s Failed to get subtitles" % (debug_pretext))
        return
    for subtitle in subtitles:
        try:
            filename = re.compile('<B>(.+?)</B>').findall(subtitle)[0]
            id = re.compile('<a href="(.+?)"').findall(subtitle)[0]
            id = '%s%s' % (tvshow_url, id)
            try:
                uploader = re.compile('<B>(.+?)</B>').findall(subtitle)[1]
                filename = '[%s] %s' % (uploader, filename)
            except:
                pass
            try:
                downloads = re.compile('<B>(.+?)</B>').findall(subtitle)[-1]
                filename += ' [%s DLs]' % (downloads)
            except:
                pass
            try:
                rating = get_rating(downloads)
            except:
                rating = 0
                pass
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        except:
            pass
    return

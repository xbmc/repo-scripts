# -*- coding: utf-8 -*- 

import sys
import os
import re
import time
import urllib
import urllib2
import xbmc
import xbmcgui
import string
import shutil
from utilities import log, toOpenSubtitles_two, twotofull
from xml.dom import minidom


  
_ = sys.modules[ "__main__" ].__language__

user_agent = 'Mozilla/5.0 (compatible; XBMC.Subtitle; XBMC)'

apikey = 'db81cb96baf8'
apiurl = 'api.betaseries.com'


def get_languages(languages):
    if languages == 'VF':
        code = 'fr'
    if languages == 'VO':
        code = 'en'
    if languages == 'VOVF':
        code = 'fr'
    return code 

def geturl(url):
    log( __name__ , " Getting url: %s" % (url))
    try:
        response = urllib2.urlopen(url)
        content = response.read()
    except:
        log( __name__ , " Failed to get url:%s" % (url))
        content = None
    return(content)

def getShortTV(title):

    try:
        # search TVDB's id from tvshow's title
        query = "select c12 from tvshow where c00 = '" + unicode(title) + "' limit 1"
        res = xbmc.executehttpapi("queryvideodatabase(" + query + ")")
        
        # get the result
        tvdbid = re.search('field>(.*?)<\/field',res)
        tvdbid = tvdbid.group(1)
        
        # get tvshow's url from TVDB's id
        searchurl = 'http://' + apiurl + '/shows/display/' + tvdbid + '.xml?key=' + apikey
        log( __name__ , " BetaSeries query : %s" % (searchurl))

        dom = minidom.parse(urllib.urlopen(searchurl))
        url = ""
        if len(dom.getElementsByTagName('url')):
            url = dom.getElementsByTagName('url')[0].childNodes[0]
            url = url.nodeValue

        return url
        
        log( __name__ , "'%s %s %s %s'" % (user, password, searchurl, url))

    except:
        log( __name__ , "getShortTV() failed")
        return url


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""

    lang1 = toOpenSubtitles_two(lang1)
    lang2 = toOpenSubtitles_two(lang2)
    lang3 = toOpenSubtitles_two(lang3)
    querylang = ""
    if lang1 == 'en' or lang2 == 'en' or lang3 == 'en': querylang = "VO"
    if lang1 == 'fr' or lang2 == 'fr' or lang3 == 'fr': querylang += "VF"
    log( __name__ , "query language: '%s'" % (querylang))

    if len(file_original_path) > 0:

        show = getShortTV(tvshow)
        if len(show)>0:

            searchurl = 'http://' + apiurl + '/subtitles/show/' + show + '.xml?season=' + season + '&episode=' + episode + '&language=' + querylang + '&key=' + apikey
            log( __name__ , "searchurl = '%s'" % (searchurl))

            try:
                # parsing shows from xml
                dom = minidom.parse(urllib.urlopen(searchurl))
                
                #time.sleep(1)
                subtitles = dom.getElementsByTagName('subtitle')

                for subtitle in subtitles:
                    url = subtitle.getElementsByTagName('url')[0].childNodes[0]
                    url = url.nodeValue

                    filename = subtitle.getElementsByTagName('file')[0].childNodes[0]
                    filename = filename.nodeValue

                    language = subtitle.getElementsByTagName('language')[0].childNodes[0]
                    language = get_languages(language.nodeValue)

                    rating = subtitle.getElementsByTagName('quality')[0].childNodes[0]
                    #rating = rating.nodeValue
                    rating = str(int(round(float(rating.nodeValue) / 5 * 9)))

                    ext = os.path.splitext(filename)[1]
                    #log( __name__ , "file : '%s' ext : '%s'" % (filename,ext))
                    if ext == '.zip':
                        if len(subtitle.getElementsByTagName('content'))>0:
                            #log( __name__ , "zip content ('%s')" % (filename))
                            content = subtitle.getElementsByTagName('content')[0]
                            items = content.getElementsByTagName('item')

                            for item in items:
                                subfile = item.childNodes[0].nodeValue

                                #if os.path.splitext(subfile)[1] == '.zip': continue # Not supported yet ;)
                            
                                search_string = "(s%#02de%#02d)|(%d%#02d)|(%dx%#02d)" % (int(season), int(episode),int(season), int(episode),int(season), int(episode))
                                queryep = re.search(search_string, subfile, re.I)
                                #log( __name__ , "ep: %s found: %s" % (search_string,queryep))
                                if queryep == None: continue



                                langs = re.search('\.(VF|VO|en|fr)\..*.{3}$',subfile,re.I)
                                #langs = langs.group(1)
                                #log( __name__ , "detect language... %s" % (subfile))
                                try:
                                    langs = langs.group(1)
                                    lang = {
                                    "fr": 'fr',
                                    "FR": 'fr',
                                    "en": 'en',
                                    "EN": 'en',
                                    "VF": 'fr',
                                    "vf": 'fr',
                                    "VO": 'en',
                                    "vo": 'en'
                                    }[langs]
                                    #log( __name__ , "language: %s" % (lang))
                                except:
                                    lang = language
                                
                                if lang != lang1 and lang != lang2 and lang != lang3: continue

                                #log( __name__ , "subfile = '%s'" % (subfile))
                                subtitles_list.append({'filename': subfile,'link': url,'language_name': twotofull(lang),'language_id':"0",'language_flag':'flags/' + lang + '.gif',"rating":rating,"sync": False})
                        else:
                            log( __name__ , "not valid content! dumping XML...")
                            log( __name__ , dom.toxml())

                    else:
                        #log( __name__ , "sub found ('%s')" % (filename))
                        subtitles_list.append({'filename': filename,'link': url,'language_name': twotofull(language),'language_id':"0",'language_flag':'flags/' + language + '.gif',"rating":rating,"sync": False})

            except:
                return subtitles_list, "", msg #standard output

    return subtitles_list, "", msg #standard output

    

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    link = subtitles_list[pos][ "link" ]
    language = subtitles_list[pos][ "language_name" ]
    filename = subtitles_list[pos][ "filename" ]
    content = geturl(link)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            log( __name__ ,"fichier RAR") #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.rar")
            log( __name__ ,"local_tmp_file %s" % (local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "betaseries.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        try:
            log( __name__ ,"Writing %s" % (local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"Failed to save subtitles to '%s'" % (local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,"nombre de fichiers %s" % (init_filecount)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            log( __name__ ,"extraction... %s" % (local_tmp_file)) #EGO
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
            else:
                log( __name__ ,"Unpacked files in '%s'" % (tmp_sub_dir))
                if os.path.exists(os.path.join(tmp_sub_dir, filename)):
                    file = str(os.path.normpath(os.path.join(tmp_sub_dir, filename)))
                    log( __name__ ,"selected file : '%s'" % ( file))
                    ext = os.path.splitext(file)[1]
                    if ext == '.zip':
                        log( __name__ ,"target file is zipped, copy to '%s'" % (zip_subs))
                        shutil.copy(file, zip_subs)
                        return True, language, ""

                    subs_file = file

        return False, language, subs_file #standard output

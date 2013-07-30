# -*- coding: utf-8 -*-

# based on argenteam.net subtitles, based on a mod of Subdivx.com subtitles, based on a mod of Undertext subtitles
# developed by quillo86 and infinito for Subtitulos.es and XBMC.org
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__


main_url = "http://www.subtitulos.es/"
debug_pretext = "subtitulos.es"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================


subtitle_pattern1 = "<div id=\"version\" class=\"ssdiv\">(.+?)Versi&oacute;n(.+?)<span class=\"right traduccion\">(.+?)</div>(.+?)</div>"
subtitle_pattern2 = "<li class='li-idioma'>(.+?)<strong>(.+?)</strong>(.+?)<li class='li-estado (.+?)</li>(.+?)<span class='descargar (.+?)</span>"

#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode):

    if re.search(r'\([^)]*\)', tvshow):
        for level in range(4):
            searchstring, tvshow, season, episode = getsearchstring(tvshow, season, episode, level)
            url = main_url + searchstring
            getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode)
    else:
        searchstring, tvshow, season, episode = getsearchstring(tvshow, season, episode, 0)
        url = main_url + searchstring
        getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode)

def getallsubsforurl(url, languageshort, langlong, file_original_path, subtitles_list, tvshow, season, episode):

    content = geturl(url)

    for matches in re.finditer(subtitle_pattern1, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
                filename = urllib.unquote_plus(matches.group(2))
                filename = re.sub(r' ', '.', filename)
                filename = re.sub(r'\s', '.', tvshow) + "." + season + "x" + episode + filename

                server = filename
                backup = filename
                subs = matches.group(4)

                for matches in re.finditer(subtitle_pattern2, subs, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
                        #log( __name__ ,"Descargas: %s" % (matches.group(2)))

                        idioma = matches.group(2)
                        idioma = re.sub(r'\xc3\xb1', 'n', idioma)
                        idioma = re.sub(r'\xc3\xa0', 'a', idioma)
                        idioma = re.sub(r'\xc3\xa9', 'e', idioma)

                        if idioma == "English":
                                languageshort = "en"
                                languagelong = "English"
                                filename = filename + ".(ENGLISH)"
                                server = filename
                        elif idioma == "Catala":
                                languageshort = "ca"
                                languagelong = "Catalan"
                                filename = filename + ".(CATALA)"
                                server = filename
                        elif idioma == "Espanol (Latinoamerica)":
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(LATINO)"
                                server = filename
                        elif idioma == "Galego":
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(GALEGO)"
                                server = filename
                        else:
                                languageshort = "es"
                                languagelong = "Spanish"
                                filename = filename + ".(ESPAÑA)"
                                server = filename

                        estado = matches.group(4)
                        estado = re.sub(r'\t', '', estado)
                        estado = re.sub(r'\n', '', estado)

                        id = matches.group(6)
                        id = id[44:62]
                        id = re.sub(r'"', '', id)

                        if estado == "green'>Completado" and languagelong == langlong:
                                subtitles_list.append({'rating': "0", 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

                        filename = backup
                        server = backup


def geturl(url):
        class AppURLopener(urllib.FancyURLopener):
                version = "App/1.7"
                def __init__(self, *args):
                        urllib.FancyURLopener.__init__(self, *args)
                def add_referrer(self, url=None):
                        if url:
                                urllib._urlopener.addheader('Referer', url)

        urllib._urlopener = AppURLopener()
        urllib._urlopener.add_referrer("http://www.subtitulos.es/")
        try:
                response = urllib._urlopener.open(url)
                content    = response.read()
        except:
                #log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
                content    = None
        return content

def getsearchstring(tvshow, season, episode, level):

    # Clean tv show name
    if level == 1 and re.search(r'\([^)][a-zA-Z]*\)', tvshow):
        # Series name like "Shameless (US)" -> "Shameless US"
        tvshow = tvshow.replace('(', '').replace(')', '')

    if level == 2 and re.search(r'\([^)][0-9]*\)', tvshow):
        # Series name like "Scandal (2012)" -> "Scandal"
        tvshow = re.sub(r'\s\([^)]*\)', '', tvshow)

    if level == 3 and re.search(r'\([^)]*\)', tvshow):
        # Series name like "Shameless (*)" -> "Shameless"
        tvshow = re.sub(r'\s\([^)]*\)', '', tvshow)

    # Zero pad episode
    episode = str(episode).rjust(2, '0')

    # Build search string
    searchstring = tvshow + '/' + season + 'x' + episode

    # Replace spaces with dashes
    searchstring = re.sub(r'\s', '-', searchstring)

    #log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))
    return searchstring, tvshow, season, episode

def clean_subtitles_list(subtitles_list):
    seen = set()
    subs = []
    for sub in subtitles_list:
        filename = sub['filename']
        #log(__name__, "Filename: %s" % filename)
        if filename not in seen:
            subs.append(sub)
            seen.add(filename)
    return subs

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""

    if len(tvshow) == 0:
            msg = "Subtitulos.es is only for TV Shows subtitles!"

    if lang1 == "Spanish":
            languagelong = "Spanish"
            languageshort = "es"
            getallsubs("es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang1 == "English":
            languagelong = "English"
            languageshort = "en"
            getallsubs("en", "English", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang1 == "Catalan":
            languagelong = "Catalan"
            languageshort = "ca"
            getallsubs("ca", "Catalan", file_original_path, subtitles_list, tvshow, season, episode)

    if lang2 == "Spanish" and lang1 != "Spanish":
            languagelong = "Spanish"
            languageshort = "es"
            getallsubs("es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang2 == "English" and lang1 != "English":
            languagelong = "English"
            languageshort = "en"
            getallsubs("en", "English", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang2 == "Catalan" and lang1 != "Catalan":
            languagelong = "Catalan"
            languageshort = "ca"
            getallsubs("ca", "Catalan", file_original_path, subtitles_list, tvshow, season, episode)

    if lang3 == "Spanish" and lang1 != "Spanish" and lang2 != "Spanish":
            languagelong = "Spanish"
            languageshort = "es"
            getallsubs("es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang3 == "English" and lang1 != "English" and lang2 != "English":
            languagelong = "English"
            languageshort = "en"
            getallsubs("en", "English", file_original_path, subtitles_list, tvshow, season, episode)
    elif lang3 == "Catalan" and lang1 != "Catalan" and lang2 != "Catalan":
            languagelong = "Catalan"
            languageshort = "ca"
            getallsubs("ca", "Catalan", file_original_path, subtitles_list, tvshow, season, episode)

    if ((lang1 != "Spanish") and (lang2 != "English") and (lang3 != "Catalan")):
        msg = "Won't work, subtitulos.es is only for Spanish, English and Catalan subtitles!"

    subtitles_list = clean_subtitles_list(subtitles_list)
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    server = subtitles_list[pos][ "server" ]
    language = subtitles_list[pos][ "language_name" ]

    url = "http://www.subtitulos.es/" + id

    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            #log( __name__ ,"%s argenteam: el contenido es RAR" % (debug_pretext)) #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "argenteam.rar")
            #log( __name__ ,"%s argenteam: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "argenteam.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            #log( __name__ ,"%s argenteam: escribo en %s" % (debug_pretext, local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            pass
            #log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            #log( __name__ ,"%s argenteam: nÃºmero de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
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
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        return False, language, subs_file #standard output

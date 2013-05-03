# -*- coding: utf-8 -*-

# Subdivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__


main_url = "http://www.subdivx.com/"
debug_pretext = "subdivx"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================


#Subtitle pattern example:
"""
<div id="menu_titulo_buscador"><a class="titulo_menu_izq" href="http://www.subdivx.com/X6XMjEzMzIyX-iron-man-2-2010.html">Iron Man 2 (2010)</a></div>
<img src="img/calif5.gif" class="detalle_calif">
</div><div id="buscador_detalle">
<div id="buscador_detalle_sub">Para la versión Iron.Man.2.2010.480p.BRRip.XviD.AC3-EVO, sacados de acá. ¡Disfruten!</div><div id="buscador_detalle_sub_datos"><b>Downloads:</b> 4673 <b>Cds:</b> 1 <b>Comentarios:</b> <a rel="nofollow" href="popcoment.php?idsub=MjEzMzIy" onclick="return hs.htmlExpand(this, { objectType: 'iframe' } )">14</a> <b>Formato:</b> SubRip <b>Subido por:</b> <a class="link1" href="http://www.subdivx.com/X9X303157">TrueSword</a> <img src="http://www.subdivx.com/pais/2.gif" width="16" height="12"> <b>el</b> 06/09/2010  <a rel="nofollow" target="new" href="http://www.subdivx.com/bajar.php?id=213322&u=6"><img src="bajar_sub.gif" border="0"></a></div></div>
<div id="menu_detalle_buscador">
"""

subtitle_pattern =  "<div\sid=\"buscador_detalle_sub\">(.+?)</div><div\sid=\"buscador_detalle_sub_datos\"><b>Downloads:</b>(.+?)<b>Cds:</b>(.+?)<b>Comentarios:</b>\s.+?\s<b>Formato:</b>.+?<b>Subido\spor:</b>\s<a\sclass=\"link1\"\shref=.+?</a>\s<.+?>.*?<a\srel=\"nofollow\"\starget=\"new\"\shref=\"http://www.subdivx.com/bajar.php\?id=(.+?)&u=(.+?)\">"
# group(1) = user comments, may content filename, group(2)= downloads used for ratings, group(3) = #files, group(4) = id, group(5) = server



#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list):
    page = 1
    if languageshort == "es":
        url = main_url + "index.php?accion=5&masdesc=&oxdown=1&pg=" + str(page) + "&buscar=" + urllib.quote_plus(searchstring)

    content = geturl(url)
    log( __name__ ,u"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
    while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
            id = matches.group(4)
            no_files = matches.group(3)
            server = matches.group(5)
            downloads = int(re.sub(r',','',matches.group(2))) / 1000
            if (downloads > 10):
                downloads=10
            filename = string.strip(matches.group(1))
            #Remove new lines on the commentaries
            filename = re.sub('\n',' ',filename)
            #Remove HTML tags on the commentaries
            filename = re.sub(r'<[^<]+?>','', filename)
            #Find filename on the comentaries to show sync label
            filesearch = os.path.split(file_original_path)
            sync = False
            if re.search(filesearch[1][:len(filesearch[1])-4], filename):
                sync = True
            try:    
                log( __name__ ,u"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            except:
                pass
            #Find filename on the commentaries and put it in front
            title_first_word = re.split('[\W]+', searchstring)
            version = re.search(title_first_word[0],filename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)
            if version != None:
                filename = filename[version.start():] + " " + filename[: version.start()]
            subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'sync': sync, 'id' : id, 'server' : server, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
        page = page + 1
        url = main_url + "index.php?accion=5&masdesc=&oxdown=1&pg=" + str(page) + "&buscar=" + urllib.quote_plus(searchstring)
        content = geturl(url)

    # Bubble sort, to put syncs on top
    for n in range(0,len(subtitles_list)):
        for i in range(1, len(subtitles_list)):
            temp = subtitles_list[i]
            if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
                subtitles_list[i] = subtitles_list[i-1]
                subtitles_list[i-1] = temp





def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,u"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,u"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,u"%s Search string = %s" % (debug_pretext, searchstring))

    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list)

    if spanish == 0:
        msg = "Won't work, Subdivx is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    server = subtitles_list[pos][ "server" ]
    language = subtitles_list[pos][ "language_name" ]
    if string.lower(language) == "spanish":
        url = main_url + "bajar.php?id=" + id + "&u=" + server
    log( __name__ ,u"%s Fetching subtitles using url %s" % (debug_pretext, url))
    content = geturl(url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            log( __name__ ,u"%s subdivx: el contenido es RAR" % (debug_pretext)) #EGO
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.rar")
            log( __name__ ,u"%s subdivx: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "subdivx.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,u"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            log( __name__ ,u"%s subdivx: escribo en %s" % (debug_pretext, local_tmp_file)) #EGO
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,u"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,u"%s subdivx: número de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
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
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file.encode("utf-8") + "," + tmp_sub_dir.encode("utf-8") +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file.decode("utf-8"))).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,u"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,u"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,u"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file.decode("utf-8"))
        return False, language, subs_file #standard output


# -*- coding: utf-8 -*-

# Subdivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__


main_url = "http://www.argenteam.net/search/"
debug_pretext = "argenteam"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

'''
<div class="search-item-desc">
	<a href="/episode/29322/The.Mentalist.%282008%29.S01E01-Pilot">
	
<div class="search-item-desc">
	<a href="/movie/25808/Awake.%282007%29">
'''

search_results_pattern = "<div\sclass=\"search-item-desc\">(.+?)<a\shref=\"/(episode|movie)/(.+?)/(.+?)\">(.+?)</a>"

subtitle_pattern = "<div\sclass=\"links\">(.+?)<strong>Descargado:</strong>(.+?)ve(ces|z)(.+?)<div>(.+?)<a\shref=\"/subtitles/(.+?)/(.+?)\">(.+?)</a>"

#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, tvshow, season, episode):
	
	if languageshort == "es":
		#log( __name__ ,"TVShow: %s" % (tvshow))
		if len(tvshow) > 0:
			url = main_url + urllib.quote_plus(searchstring)
		else:
			#searchstring = re.sub('\([0-9]{4}\)','',searchstring)
			url = main_url + urllib.quote_plus(searchstring)
			
	content = geturl(url)
	#subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': searchstring, 'sync': False, 'id' : 1, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
	#if isinstance(season, int ) and isinstance(episode, int ):
	
	#for matches in re.finditer(search_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
		#tipo = matches.group(2)
		#id = matches.group(3)
		#link = matches.group(4)
		
		#url_subtitle = "http://www.argenteam.net/" + tipo +"/"+ id +"/"+link
		
		#content_subtitle = geturl(url_subtitle)
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
			#log( __name__ ,"Descargas: %s" % (matches.group(2)))
			
		id = matches.group(6)
		filename=urllib.unquote_plus(matches.group(7))
		server = filename
		downloads = int(matches.group(2)) / 1000
		if (downloads > 10):
			downloads=10
			#server = matches.group(4).encode('ascii')
			#log( __name__ ,"Resultado Subtítulo 2: %s" % (matches.group(6)))
		subtitles_list.append({'rating': str(downloads), 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
	
	
def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        #log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    #log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    searchstring = searchstring + ' ' + year
    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)

    if spanish == 0:
        msg = "Won't work, argenteam is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    server = subtitles_list[pos][ "server" ]
    language = subtitles_list[pos][ "language_name" ]

    if string.lower(language) == "spanish":
        url = "http://www.argenteam.net/subtitles/" + id + "/"

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
            #log( __name__ ,"%s argenteam: número de init_filecount %s" % (debug_pretext, init_filecount)) #EGO
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


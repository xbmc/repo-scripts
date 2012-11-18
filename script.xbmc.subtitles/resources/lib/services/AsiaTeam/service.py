# -*- coding: utf-8 -*-

# Asiateam.net subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, urlparse
from utilities import log


_ = sys.modules[ "__main__" ].__language__


main_url = "http://subs.asia-team.net/search.php?term=%s&mtype=0&id=0&sort=file_name&order=asc&limit=900" #url changed
debug_pretext = "asiateam"
DEBUG = True

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

subtitle_pattern = "<a href=\"file.php\?id=(.*?)\">(.*?)</a>"

#====================================================================================================================
# Functions
#====================================================================================================================


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, tvshow, season, episode):		
		
	url= main_url.replace("%s",searchstring)
	url = url.replace(' ','%20') #replace spaces
	content= geturl(url)
	log(__name__ ,"%s Getting url: %s" % (debug_pretext, content))
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
		id = matches.group(1)
		filename=matches.group(2)
		server = "http://www.asia-team.net"
		subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'server': server, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content    = response.read()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    searchstring = title

    spanish = 0
    if string.lower(lang1) == "spanish": spanish = 1
    elif string.lower(lang2) == "spanish": spanish = 2
    elif string.lower(lang3) == "spanish": spanish = 3

    getallsubs(searchstring, "es", "Spanish", file_original_path, subtitles_list, tvshow, season, episode)

    if spanish == 0:
        msg = "Won't work, Asia-Team is only for Spanish subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    filename = subtitles_list[pos][ "filename" ]
    url = "http://subs.asia-team.net/download.php?id=" + id
	
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        opener = urllib2.build_opener(SmartRedirectHandler())
        content = opener.open(req)
    except ImportError, inst:
        status,location = inst	
        response= urllib.urlopen(location)
        content=response.read()
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            log( __name__ ,"%s asia-team: el contenido es RAR" % (debug_pretext))
            local_tmp_file = os.path.join(tmp_sub_dir, filename+".rar")
            log( __name__ ,"%s asia-team: local_tmp_file %s" % (debug_pretext, local_tmp_file))
            packed = True
        elif header == 'PK':
            local_tmp_file = os.path.join(tmp_sub_dir, filename+".zip")
            packed = True
        else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
            local_tmp_file = os.path.join(tmp_sub_dir, "asia-team.srt") # assume unpacked sub file is an '.srt'
            subs_file = local_tmp_file
            packed = False
        log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
        try:
            log( __name__ ,"%s asia-team: escribo en %s" % (debug_pretext, local_tmp_file))
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            log( __name__ ,"%s asia-team: número de init_filecount %s" % (debug_pretext, init_filecount))
            filecount = init_filecount
            max_mtime = 0
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub']):
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
                    if (string.split(file,'.')[-1] in ['srt','sub']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))			
                try:
                    file = choice_one(files) #open new dialog to select file
                    subs_file = os.path.join(tmp_sub_dir,file)
                    return False, language, subs_file #standard output
                except:
                    return False, language, "" #standard output				

		
def choice_one(files):
    options = []
    sub_list = []
    Number = 0
    
    for file in files:
        if (string.split(file, '.')[-1] in ['srt','sub','txt','idx','ssa']):		
            Number = Number + 1
            options.append("%02d) %s" % (Number , file))
            sub_list.append(file)
    choice = xbmcgui.Dialog()
    selection = choice.select("Nº) SUBTITULO", options)
    log( __name__ ,"selection=%d" % (selection))
    if selection!= -1:
        return sub_list[selection]


class SmartRedirectHandler(urllib2.HTTPRedirectHandler):	
	def http_error_302(self, req, fp, code, msg, headers):
			# Some servers (incorrectly) return multiple Location headers
			# (so probably same goes for URI).  Use first header.
			if 'location' in headers:
				newurl = headers.getheaders('location')[0]
			elif 'uri' in headers:
				newurl = headers.getheaders('uri')[0]
			else:
				return
			newurl=newurl.replace(' ','%20') # <<< TEMP FIX - inserting this line temporarily fixes this problem
			newurl = urlparse.urljoin(req.get_full_url(), newurl)
			raise ImportError(302,newurl)
# -*- coding: UTF-8 -*-

import os, sys, re, shutil, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, uuid, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.subclub.eu/"
download_url = "http://www.subclub.eu/down.php?id="
debug_pretext = ""

sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi', 'txt']
packext = ['rar', 'zip']


subtitle_pattern='<a class="sc_link".+?/down.php\?id=([^"]+).+?>(.+?)</a>'

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):
    url = main_url + "jutud.php?tp=nimi&otsing=" + urllib.quote_plus(searchstring)
    content = geturl(url)
    content=content.replace('\r\n','')
    if content is not None:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        for id,filename in re.compile(subtitle_pattern).findall(content):
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
            filesearch = os.path.split(filesearch)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
            dirsearch = filesearch[0].split(os.sep)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
            dirsearch_check = string.split(dirsearch[-1], '.')
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))

            subtitles_list.append({'rating': '0', 'no_files': 1, 'filename': filename, 'sync': False, 'id' : id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

        
def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        version = ''
    my_urlopener = MyOpener()
    log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
    try:
        response = my_urlopener.open(url)
        content = response.read()
        return_url = response.geturl()
        if url != return_url:
            log( __name__ ,"%s Getting redirected url: %s" % (debug_pretext, return_url))
            if (' ' in return_url):
                log( __name__ ,"%s Redirected url contains space (workaround a bug in python redirection: 'http://bugs.python.org/issue1153027', should be solved, but isn't)" % (debug_pretext))
                return_url = return_url.replace(' ','%20')
            response = my_urlopener.open(return_url)
            content = response.read()
            return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content = None
    return content


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    searchstring_notclean = ""
    searchstring = ""
    global israr
    israr = os.path.abspath(file_original_path)
    israr = os.path.split(israr)
    israr = israr[0].split(os.sep)
    israr = string.split(israr[-1], '.')
    israr = string.lower(israr[-1])
    
    if len(tvshow) == 0:
        if 'rar' in israr and searchstring is not None:
            if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
                dirsearch = os.path.abspath(file_original_path)
                dirsearch = os.path.split(dirsearch)
                dirsearch = dirsearch[0].split(os.sep)
                if len(dirsearch) > 1:
                    searchstring_notclean = dirsearch[-3]
                    searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                    searchstring = searchstring[0]
                else:
                    searchstring = title
            else:
                searchstring = title
        elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
            dirsearch = os.path.abspath(file_original_path)
            dirsearch = os.path.split(dirsearch)
            dirsearch = dirsearch[0].split(os.sep)
            if len(dirsearch) > 1:
                searchstring_notclean = dirsearch[-2]
                searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                searchstring = searchstring[0]
            else:
                #We are at the root of the drive!!! so there's no dir to lookup only file#
                title = os.path.split(file_original_path)
                searchstring = title[-1]
        else:
            if title == "":
                title = os.path.split(file_original_path)
                searchstring = title[-1]
            else:
                searchstring = title
            
    if len(tvshow) > 0:
        searchstring = "%s %#02dx%#02d" % (tvshow, int(season), int(episode))
    log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    estonian = 0
    if string.lower(lang1) == "estonian": estonian = 1
    elif string.lower(lang2) == "estonian": estonian = 2
    elif string.lower(lang3) == "estonian": estonian = 3

    getallsubs(searchstring, "et", "Estonian", file_original_path, subtitles_list, searchstring_notclean)
    if estonian == 0:
        msg = "Won't work, subclub.eu is only for Estonian subtitles."

    return subtitles_list, "", msg #standard output
    
def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
	for extension in pattern:
	    for filename in fnmatch.filter(files, '*.' + extension):
		results.append(os.path.join(base, filename))
    return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    sync = subtitles_list[pos][ "sync" ]
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    if string.lower(language) == "estonian":
        content = opener.open(download_url + id)

    downloaded_content = content.read()
    #Create some variables
    subtitle = ""
    extract_path = os.path.join(tmp_sub_dir, "extracted")
    
    fname = os.path.join(tmp_sub_dir,str(id))
    if content.info().get('Content-Disposition').__contains__('rar'):
      fname += '.rar'
    else:
      fname += '.zip'
    f = open(fname,'wb')
    f.write(downloaded_content)
    f.close()
    
    xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
    time.sleep(2)
    subclub_tmp = []
    fs_encoding = sys.getfilesystemencoding()
    for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
      for file in files:
	dirfile = os.path.join(root, file)
	ext = os.path.splitext(dirfile)[1][1:].lower()
	if ext in sub_ext:
	  subclub_tmp.append(dirfile)
	elif os.path.isfile(dirfile):
	  os.remove(dirfile)
	  
    searchrars = recursive_glob(extract_path, packext)
    searchrarcount = len(searchrars)
    
    if searchrarcount > 1:
      for filerar in searchrars:
	if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
	  try:
	    xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
	  except:
	    return False
    time.sleep(1)
    searchsubs = recursive_glob(extract_path, sub_ext)
    searchsubscount = len(searchsubs)
    for filesub in searchsubs:
      nopath = string.split(filesub, extract_path)[-1]
      justfile = nopath.split(os.sep)[-1]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
      #log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
      releasefilename = filesearch[1][:len(filesearch[1])-4]
      releasedirname = filesearch[0].split(os.sep)
      if 'rar' in israr:
	releasedirname = releasedirname[-2]
      else:
	releasedirname = releasedirname[-1]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
      #log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
      subsfilename = justfile[:len(justfile)-4]
      #For DEBUG only uncomment next line
      #log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
      #log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
      #Check for multi CD Releases
      multicds_pattern = "\+?(cd\d)\+?"
      multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
      multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
      #Start choosing the right subtitle(s)
      if searchsubscount == 1 and sync == True:
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
	break
      elif string.lower(subsfilename) == string.lower(releasefilename):
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
	break
      elif string.lower(subsfilename) == string.lower(releasedirname):
	subs_file = filesub
	subtitle = subs_file
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
	break
      elif (multicdsubs != None) and (multicdsrls != None):
	multicdsubs = string.lower(multicdsubs.group(1))
	multicdsrls = string.lower(multicdsrls.group(1))
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
	#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
	if multicdsrls == multicdsubs:
	  subs_file = filesub
	  subtitle = subs_file
	  break

    else:
    # If there are more than one subtitle in the temp dir, launch a browse dialog
    # so user can choose. If only one subtitle is found, parse it to the addon.
      if len(subclub_tmp) > 1:
	dialog = xbmcgui.Dialog()
	subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
	if subtitle == extract_path+"/": subtitle = ""
      elif subclub_tmp:
	subtitle = subclub_tmp[0]
    
    language = subtitles_list[pos][ "language_name" ]
    return False, language, subtitle #standard output
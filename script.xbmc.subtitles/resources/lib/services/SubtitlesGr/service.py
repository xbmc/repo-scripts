# -*- coding: UTF-8 -*-

import os, sys, re, shutil, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import log
_ = sys.modules[ "__main__" ].__language__

main_url = "http://www.subtitles.gr/"
#main_url = "http://www.greeksubtitles.info/"
download_url = "http://www.findsubtitles.eu/getp.php?id="
debug_pretext = ""

subtitle_pattern='<img src=.+?flags/el.gif.+?nbsp.+?http://.+?/.+?/.+?/(.+?)/".+?">(.+?)</a>'
#subtitle_pattern="<img src=.+?flags/el.gif.+?nbsp.+?get_greek_subtitles.php.+?id=(.+?)'>(.+?)</a>"


def getallsubs(searchstring, languageshort, languagelong, subtitles_list):
    url = main_url + "search.php?name=" + urllib.quote_plus(searchstring)
    content = geturl(url)
    content=content.replace('\n','')
    if content is not None:
        log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
        for id,filename in re.compile(subtitle_pattern).findall(content):
            log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
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
    if len(tvshow) == 0:
        if str(year) == "":
            title, year = xbmc.getCleanMovieTitle( title )
        else:
            year  = year
            title = title
        searchstring = title
    if len(tvshow) > 0:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

    greek = 0
    if string.lower(lang1) == "greek": greek = 1
    elif string.lower(lang2) == "greek": greek = 2
    elif string.lower(lang3) == "greek": greek = 3

    getallsubs(searchstring, "el", "Greek", subtitles_list)
    if greek == 0:
        msg = "Won't work, subtitles.gr is only for Greek subtitles."

    return subtitles_list, "", msg #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    id = subtitles_list[pos][ "id" ]
    language = subtitles_list[pos][ "language_name" ]
    if string.lower(language) == "greek": url = download_url + id
    local_file = open(zip_subs, "w" + "b")
    f = urllib.urlopen(url)
    local_file.write(f.read())
    local_file.close()
    tmp_new_dir = os.path.join( xbmc.translatePath(tmp_sub_dir) ,"zipsubs" )
    tmp_new_dir_2 = os.path.join( xbmc.translatePath(tmp_new_dir) ,"subs" )
    if not os.path.exists(tmp_new_dir): os.makedirs(tmp_new_dir)
    if not os.path.exists(tmp_new_dir_2): os.makedirs(tmp_new_dir_2)
    xbmc.executebuiltin("XBMC.Extract(" + zip_subs + "," + tmp_new_dir +")")
    xbmc.sleep(1000)
    for file in os.listdir(tmp_new_dir_2): file = os.path.join(tmp_new_dir_2, file)
    if (file.endswith('.rar') or file.endswith('.zip')):
        xbmc.executebuiltin("XBMC.Extract(" + file + "," + tmp_sub_dir +")")
        xbmc.sleep(1000)
    else: shutil.copy(file, tmp_sub_dir)
    os.remove(zip_subs)
    shutil.rmtree(tmp_new_dir)
    return True,language, "" #standard output

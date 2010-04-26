import sys
import os
from utilities import hashFile, LOG, LOG_INFO, twotoone, toOpenSubtitles_two
from pn_utilities import OSDBServer
#import xbmc


_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__

STATUS_LABEL = 100
LOADING_IMAGE = 110
SUBTITLES_LIST = 120

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):

    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = "000000000000"
        def run(self):
            self.result = func(*args, **kwargs)
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return it.result
    else:
        return it.result
        
def set_filehash(path,rar):
    
    if rar:
      path = os.path.dirname( path )
    file_hash = hashFile(path)
    return file_hash        


def search_subtitles( file_original_path, title, tvshow, year, season, episode, debug, set_temp, rar, lang1, lang2, lang3 ): #standard input
       
    ok = False
    msg = ""
    hash_search = False
    osdb_server = OSDBServer()
    subtitles_list = []    
    language1 = twotoone(toOpenSubtitles_two(lang1))
    language2 = twotoone(toOpenSubtitles_two(lang2))
    language3 = twotoone(toOpenSubtitles_two(lang3))  
    if set_temp : 
        hash_search = False
    else:
        hashTry = timeout(set_filehash, args=(file_original_path, rar), timeout_duration=5)
        try: file_size = os.path.getsize( file_original_path ) 
        except: file_size = "000000000" 
        if file_size != "" and hashTry != "":
          hash_search = True
    
    if debug :
        print "File Size [%s]" % file_size
        print "File Hash [%s]" % hashTry
    try:

        if not set_temp :
            if debug : LOG( LOG_INFO, "Search by hash_pod [%s]" % os.path.basename( file_original_path ) )
            subtitles_list, session_id = osdb_server.searchsubtitles_pod( hashTry ,language1, language2, language3, debug)
                    
        if (len ( subtitles_list )) < 1:
            if debug : LOG( LOG_INFO,"Search by name_pod [%s]" % os.path.basename( file_original_path ) )
            
            subtitles_list = osdb_server.searchsubtitlesbyname_pod( title, tvshow, season, episode, language1, language2, language3, year, debug )
        
        return subtitles_list, "" #standard output
    except :
        return subtitles_list, "" #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    import urllib
    pod_url_parse = urllib.urlopen(subtitles_list[pos][ "link" ]).read()
    url = "http://www.podnapisi.net/ppodnapisi/download/i/%s" % (pod_url_parse.split("/ppodnapisi/download/i/")[1].split('" title="')[0])  
    local_file = open(zip_subs, "w" + "b")
    f = urllib.urlopen(url)
    local_file.write(f.read())
    local_file.close()
    
    language = subtitles_list[pos][ "language_name" ]
    return True,language, "" #standard output
    
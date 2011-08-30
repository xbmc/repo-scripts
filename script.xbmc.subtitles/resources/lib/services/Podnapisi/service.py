# -*- coding: utf-8 -*- 

import sys
import os
from utilities import hashFile, twotoone, toOpenSubtitles_two, log
from pn_utilities import OSDBServer
import xbmc
import urllib
import threading

_ = sys.modules[ "__main__" ].__language__

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None): 
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


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input     
  ok = False
  msg = ""
  osdb_server = OSDBServer()
  osdb_server.create()    
  subtitles_list = []
  file_size = ""
  hashTry = ""
  language1 = twotoone(toOpenSubtitles_two(lang1))
  language2 = twotoone(toOpenSubtitles_two(lang2))
  language3 = twotoone(toOpenSubtitles_two(lang3))  
  if set_temp : 
    hash_search = False      
  else:
    try:
      try:
        file_size, hashTry = xbmc.subHashAndFileSize(file_original_path)
        log( __name__ ,"xbmc module hash and size")
      except:  
        hashTry = timeout(set_filehash, args=(file_original_path, rar), timeout_duration=5)
        file_size = str(os.path.getsize( file_original_path ))
      hash_search = True
    except: 
      hash_search = False 
  
  if file_size != "": log( __name__ ,"File Size [%s]" % file_size )
  if hashTry != "":   log( __name__ ,"File Hash [%s]" % hashTry)
  if hash_search :
    log( __name__ ,"Search for [%s] by hash" % (os.path.basename( file_original_path ),))
    subtitles_list, session_id = osdb_server.searchsubtitles_pod( hashTry ,language1, language2, language3, stack)
  if not subtitles_list:
    log( __name__ ,"Search for [%s] by name" % (os.path.basename( file_original_path ),))
    subtitles_list = osdb_server.searchsubtitlesbyname_pod( title, tvshow, season, episode, language1, language2, language3, year, stack )
  return subtitles_list, "", "" #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
  osdb_server = OSDBServer()
  url = osdb_server.download(session_id, subtitles_list[pos][ "link" ])
  if url != None:
    local_file = open(zip_subs, "w" + "b")
    f = urllib.urlopen(url)
    local_file.write(f.read())
    local_file.close()
  
  language = subtitles_list[pos][ "language_name" ]
  return True,language, "" #standard output
    
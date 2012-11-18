# -*- coding: utf-8 -*- 

import sys
import os
from utilities import languageTranslate, log, hashFile
from pn_utilities import OSDBServer
import xbmc
import urllib

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input     
  ok = False
  msg = ""
  osdb_server = OSDBServer()
  osdb_server.create()    
  subtitles_list = []
  file_size = ""
  hashTry = ""
  language1 = languageTranslate(lang1,0,1)
  language2 = languageTranslate(lang2,0,1)
  language3 = languageTranslate(lang3,0,1)  
  if set_temp : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      file_size, SubHash = hashFile(file_original_path, False)
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  if hash_search :
    log( __name__ ,"Search for [%s] by hash" % (os.path.basename( file_original_path ),))
    subtitles_list, session_id = osdb_server.searchsubtitles_pod( SubHash ,language1, language2, language3, stack)
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
    
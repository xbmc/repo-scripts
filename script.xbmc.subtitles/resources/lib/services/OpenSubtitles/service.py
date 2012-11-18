# -*- coding: utf-8 -*- 

import sys
import os
from utilities import log, hashFile
from os_utilities import OSDBServer
import xbmc

_ = sys.modules[ "__main__" ].__language__   

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
  ok = False
  msg = ""
  hash_search = False
  subtitles_list = []  
  if len(tvshow) > 0:                                            # TvShow
    OS_search_string = ("%s S%.2dE%.2d" % (tvshow,
                                           int(season),
                                           int(episode),)
                                          ).replace(" ","+")      
  else:                                                          # Movie or not in Library
    if str(year) == "":                                          # Not in Library
      title, year = xbmc.getCleanMovieTitle( title )
    else:                                                        # Movie in Library
      year  = year
      title = title
    OS_search_string = title.replace(" ","+")
  log( __name__ , "Search String [ %s ]" % (OS_search_string,))     
 
  if set_temp : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      file_size, SubHash = hashFile(file_original_path, rar)
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  
  log( __name__ ,"Search by hash and name %s" % (os.path.basename( file_original_path ),))
  subtitles_list, msg = OSDBServer().searchsubtitles( OS_search_string, lang1, lang2, lang3, hash_search, SubHash, file_size  )
      
  return subtitles_list, "", msg #standard output
  


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
  
  destination = os.path.join(tmp_sub_dir, "%s.srt" % subtitles_list[pos][ "ID" ])
  result = OSDBServer().download(subtitles_list[pos][ "ID" ], destination, session_id)
  if not result:
    import urllib
    urllib.urlretrieve(subtitles_list[pos][ "link" ],zip_subs)
  
  language = subtitles_list[pos][ "language_name" ]
  return not result,language, destination #standard output
    
    
    
    

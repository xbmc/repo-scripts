import sys
import os
from ss_utilities import OSDBServer
from utilities import twotoone, toOpenSubtitles_two
import xbmc

_ = sys.modules[ "__main__" ].__language__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    osdb_server = OSDBServer()
    subtitles_list = []
    language1 = lang1
    language2 = lang2
    language3 = lang3
    try:
        if (len ( subtitles_list )) < 1:            
            xbmc.output("[SubtitleSource] - Search for [%s] by name" % (os.path.basename( file_original_path ),),level=xbmc.LOGDEBUG )
            subtitles_list = osdb_server.searchsubtitlesbyname_ss(title, tvshow, season, episode, language1, language2, language3, year)
        return subtitles_list, "", "" #standard output
    
    except :
        return subtitles_list, "", "" #standard output
                
    
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    local_tmp_file = os.path.join(tmp_sub_dir, "subtitlesource_subs.srt")
    import urllib
    response = urllib.urlopen(subtitles_list[pos][ "link" ])
    xbmc.output("[SubtitleSource] - Downloading subtitle: [%s]" % (subtitles_list[pos][ "filename" ]),level=xbmc.LOGDEBUG )
    local_file_handle = open(local_tmp_file, "w" + "b")
    local_file_handle.write(response.read())
    local_file_handle.close()

    language = subtitles_list[pos][ "language_name" ]
    return False, language, local_tmp_file #standard output


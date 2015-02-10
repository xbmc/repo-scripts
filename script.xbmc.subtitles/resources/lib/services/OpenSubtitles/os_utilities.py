# -*- coding: utf-8 -*- 

import os
import sys
import xmlrpclib
from utilities import *

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__

BASE_URL_XMLRPC = u"http://api.opensubtitles.org/xml-rpc"

class OSDBServer:

  def __init__( self, *args, **kwargs ):
    self.server = xmlrpclib.Server( BASE_URL_XMLRPC, verbose=0 )
    login = self.server.LogIn("", "", "en", "%s_v%s" %(__scriptname__.replace(" ","_"),__version__))    
    self.osdb_token  = login[ "token" ]

  def mergesubtitles( self ):
    self.subtitles_list = []
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list.sort(key=lambda x: [not x['sync'],x['lang_index']])

  def searchsubtitles( self, srch_string , lang1,lang2,lang3,hash_search, _hash = "000000000", size = "000000000"):
    msg                      = ""
    lang_index               = 3
    searchlist               = []
    self.subtitles_hash_list = []
    self.langs_ids           = [languageTranslate(lang1,0,2), languageTranslate(lang2,0,2), languageTranslate(lang3,0,2)]    
    language                 = languageTranslate(lang1,0,3)
    
    if lang1 != lang2:
      language += "," + languageTranslate(lang2,0,3)
    if lang3 != lang1 and lang3 != lang2:
      language += "," + languageTranslate(lang3,0,3)
  
    log( __name__ ,"Token:[%s]" % str(self.osdb_token))
  
    try:
      if ( self.osdb_token ) :
        if hash_search:
          searchlist.append({'sublanguageid':language, 'moviehash':_hash, 'moviebytesize':str( size ) })
        searchlist.append({'sublanguageid':language, 'query':srch_string })
        search = self.server.SearchSubtitles( self.osdb_token, searchlist )
        if search["data"]:
          for item in search["data"]:
            if item["ISO639"]:
              lang_index=0
              for user_lang_id in self.langs_ids:
                if user_lang_id == item["ISO639"]:
                  break
                lang_index+=1
              flag_image = "flags/%s.gif" % item["ISO639"]
            else:                                
              flag_image = "-.gif"

            if str(item["MatchedBy"]) == "moviehash":
              sync = True
            else:                                
              sync = False

            self.subtitles_hash_list.append({'lang_index'    : lang_index,
                                             'filename'      : item["SubFileName"],
                                             'link'          : item["ZipDownloadLink"],
                                             'language_name' : item["LanguageName"],
                                             'language_flag' : flag_image,
                                             'language_id'   : item["SubLanguageID"],
                                             'ID'            : item["IDSubtitleFile"],
                                             'rating'        : str(int(item["SubRating"][0])),
                                             'format'        : item["SubFormat"],
                                             'sync'          : sync,
                                             'hearing_imp'   : int(item["SubHearingImpaired"]) != 0
                                             })
            
    except:
      msg = "Error Searching For Subs"
    
    self.mergesubtitles()
    return self.subtitles_list, msg

  def download(self, ID, dest, token):
     try:
       import zlib, base64
       down_id=[ID,]
       result = self.server.DownloadSubtitles(self.osdb_token, down_id)
       if result["data"]:
         local_file = open(dest, "w" + "b")
         d = zlib.decompressobj(16+zlib.MAX_WBITS)
         data = d.decompress(base64.b64decode(result["data"][0]["data"]))
         local_file.write(data)
         local_file.close()
         return True
       return False
     except:
       return False
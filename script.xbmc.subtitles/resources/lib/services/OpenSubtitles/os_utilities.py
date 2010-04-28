import sys
import os
import xmlrpclib
from utilities import *



_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__

BASE_URL_XMLRPC = u"http://api.opensubtitles.org/xml-rpc"

def compare_columns(b,a):
        return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] ) 

class OSDBServer:

###-------------------------- Merge Subtitles All -------------################


    def mergesubtitles( self ):
        self.subtitles_list = []
        if( len ( self.subtitles_hash_list ) > 0 ):
            for item in self.subtitles_hash_list:
                if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
                    self.subtitles_list.append( item )


        if( len ( self.subtitles_list ) > 0 ):
            self.subtitles_list = sorted(self.subtitles_list, compare_columns)



###-------------------------- Opensubtitles Search -------------################
        

    def searchsubtitles( self, srch_string , lang1,lang2,lang3,hash_search, debug, _hash = "000000000", size = "000000000"):
        
        self.subtitles_hash_list = []
        self.subtitles_list =[]
        osdb_token  = ""
        
        server = xmlrpclib.Server( BASE_URL_XMLRPC, verbose=0 )
        login = server.LogIn("", "", "en", "OpenSubtitles_OSD")
    
        osdb_token  = login[ "token" ]
        if debug : LOG( LOG_INFO, "Token:[%s]" % str(osdb_token) )
    
                        
        language = toOpenSubtitlesId(lang1)
        if lang1 != lang2:
            language += "," + toOpenSubtitlesId(lang2)
        if lang3 != lang1 and lang3 != lang2:
            language += "," + toOpenSubtitlesId(lang3)
                
        try:
            if (osdb_token) :
                searchlist = []
                if hash_search :
                    searchlist.append({'sublanguageid':language,'moviehash':_hash ,'moviebytesize':str( size ) })
                searchlist.append({ 'sublanguageid':language, 'query':srch_string })
                search = server.SearchSubtitles( osdb_token, searchlist )
    
                if search["data"]:
                    for item in search["data"]:
                        if item["ISO639"]:
                                flag_image = "flags/" + item["ISO639"] + ".gif"
                        else:                                                           
                                flag_image = "-.gif"

                        if str(item["MatchedBy"]) == "moviehash":
                                sync = True
                        else:                                                           
                                sync = False
                                
                        self.subtitles_hash_list.append({'filename':item["SubFileName"],'link':item["ZipDownloadLink"],"language_name":item["LanguageName"],"language_flag":flag_image,"language_id":item["SubLanguageID"],"ID":item["IDSubtitle"],"rating":str( int( item["SubRating"][0] ) ),"format":item["SubFormat"],"sync":sync})

                    self.mergesubtitles()
                    return self.subtitles_list
                                
    
            else: 
                return self.subtitles_list
                        
        except:
            return self.subtitles_list
        
        


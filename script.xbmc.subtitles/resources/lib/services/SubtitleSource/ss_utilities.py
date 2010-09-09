import sys
import os
from utilities import twotoone, toOpenSubtitles_two
import xbmc
import re

_ = sys.modules[ "__main__" ].__language__

def compare_columns(b,a):
        return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] )

class OSDBServer:
    
###-------------------------- Merge Subtitles All -------------################
    
    def mergesubtitles( self ):
        self.subtitles_list = []
        if( len ( self.subtitles_name_list ) > 0 ):
            for item in self.subtitles_name_list:
                if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
                    if item["no_files"] < 2:
                        self.subtitles_list.append( item )


        if( len ( self.subtitles_list ) > 0 ):
            self.subtitles_list = sorted(self.subtitles_list, compare_columns)


###-------------------------- Subtitles By Name -------------################

    def searchsubtitlesbyname_ss( self, name, tvshow, season, episode, lang1, lang2, lang3, year ):
        from xml.dom import minidom
        import urllib        
        self.subtitles_list = []
        self.subtitles_name_list = []
        search_url1 = None
        search_url2 = None
        if len(tvshow) > 1:
            name = tvshow+".S"+str(season)+"E"+str(episode) 

        name = name.replace(" ","+")
                
        search_url = "http://www.subtitlesource.org/api/xmlsearch/"+name+"/"+lang1+"/0"
        xbmc.output("[SubtitleSource] - Search URL: [%s]" % (search_url),level=xbmc.LOGDEBUG )
        
        if lang2!=lang1:
            search_url1 = "http://www.subtitlesource.org/api/xmlsearch/"+name+"/"+lang2+"/0"
            xbmc.output("[SubtitleSource] - Search URL1: [%s]" % (search_url1),level=xbmc.LOGDEBUG )  
        if lang3!=lang1 and lang3!=lang2:
            search_url2 = "http://www.subtitlesource.org/api/xmlsearch/"+name+"/"+lang3+"/0"
            xbmc.output("[SubtitleSource] - Search URL2: [%s]" % (search_url2),level=xbmc.LOGDEBUG )

        try:

            socket = urllib.urlopen(search_url)
            result = socket.read()
            socket.close()
            xmldoc = minidom.parseString(result)
            subs = xmldoc.getElementsByTagName("sub")
            
            if search_url1 is not None: 
                socket = urllib.urlopen( search_url1 )
                result = socket.read()
                socket.close()
                xmldoc = minidom.parseString(result)
                subs1 = xmldoc.getElementsByTagName("sub")
                subs = subs + subs1              
                
            if search_url2 is not None: 
                socket = urllib.urlopen( search_url2 )
                result = socket.read()
                socket.close()
                xmldoc = minidom.parseString(result)
                subs1 = xmldoc.getElementsByTagName("sub")
                subs = subs + subs1
            
            if subs:
                xbmc.output("[SubtitleSource] - Subtitles Found",level=xbmc.LOGDEBUG )
                url_base = "http://www.subtitlesource.org/download/text/"
                
                for sub in subs:
                        
                    filename = ""
                    movie = ""
                    languagename = ""
                    subtitle_id = 0
                    lang_id = ""
                    flag_image = ""
                    link = ""
                    format = "srt"
                    no_files = ""
                            
                    if sub.getElementsByTagName("title")[0].firstChild:
                        movie = sub.getElementsByTagName("title")[0].firstChild.data
                    
                    if sub.getElementsByTagName("releasename")[0].firstChild:
                        filename = sub.getElementsByTagName("releasename")[0].firstChild.data
                    filename = "%s.srt" % (filename,)
                    
                    rating = 0
                    
                    if sub.getElementsByTagName("language")[0].firstChild:
                        languagename = sub.getElementsByTagName("language")[0].firstChild.data
                    
                    lang_id = toOpenSubtitles_two(languagename)
                    lang_id = twotoone(lang_id)
            
                    flag_image = "flags/%s.gif" % ( toOpenSubtitles_two(languagename), )
                            
                    if sub.getElementsByTagName("id")[0].firstChild:
                        subtitle_id = sub.getElementsByTagName("id")[0].firstChild.data
                       
                    link = "%s%s/1" % ( url_base,str(subtitle_id), )
                    if sub.getElementsByTagName("cd")[0].firstChild:
                        no_files = int(sub.getElementsByTagName("cd")[0].firstChild.data)   
                                    
                    self.subtitles_name_list.append({'filename':filename,'link':link,'movie':movie,"ID":subtitle_id,'language_name':languagename,'language_id':lang_id,'language_flag':flag_image,"format":format,"rating":str(rating),"sync":False, "no_files":no_files})
                          
                    self.mergesubtitles()                  
                return self.subtitles_list
            else:
                return self.subtitles_list

        except :
            return self.subtitles_list


import sys
import os
import xmlrpclib
from utilities import *
import xbmc


_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__



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

        if( len ( self.subtitles_name_list ) > 0 ):
            for item in self.subtitles_name_list:
                if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
                    if item["no_files"] < 2:
                        self.subtitles_list.append( item )


        if( len ( self.subtitles_list ) > 0 ):
            self.subtitles_list = sorted(self.subtitles_list, compare_columns)




###-------------------------- Podnapisi Hash -------------################


    def searchsubtitles_pod( self, movie_hash, lang1,lang2,lang3):
        self.subtitles_hash_list = []
        pod_session = ""
        self.subtitles_list = []
        podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')
    
        lang = []
        lang11 = lang1
        lang.append(lang11)
        if lang1!=lang2:
            lang22 = lang2
            lang.append(lang22)
        if lang3!=lang2 and lang3!=lang1:
            lang33 = lang3
            lang.append(lang33)
        hash_pod =[]
        hash_pod.append(movie_hash)
        xbmc.output("Languages : [%s]\nHash : [%s]" % (str(lang),str(hash_pod),), level=xbmc.LOGDEBUG )
        try:
    
            init = podserver.initiate("OpenSubtitles_OSD")
            try:
                from hashlib import md5 as md5
                from hashlib import sha256 as sha256
            except ImportError:
                from md5 import md5
                import sha256
    
    
            username = __settings__.getSetting( "PNuser" )
            password = __settings__.getSetting( "PNpass" )
    
            hash = md5()
            hash.update(password)
            password = hash.hexdigest()
    
            password256 = sha256.sha256(str(password) + str(init['nonce'])).hexdigest()
            if str(init['status']) == "200":
                pod_session = init['session']
    
                auth = podserver.authenticate(pod_session, username, password256)
                filt = podserver.setFilters(pod_session, True, lang , False)
                
                xbmc.output("Filter : [%s]\nAuth : [%s]" % (str(filt),str(auth),),level=xbmc.LOGDEBUG  )                                              
                
                search = podserver.search(pod_session , hash_pod)
    
                if str(search['status']) == "200" and len(search['results']) :
                    item1 = search["results"]
                    item2 = item1[movie_hash]
                    item3 = item2["subtitles"]
    
                    episode = item2["tvEpisode"]
    
                    if str(episode) == "0":
                        title = "%s (%s)" % (str(item2["movieTitle"]),str(item2["movieYear"]),)
                    else:
                        title = "%s S(%s)E(%s)" % (str(item2["movieTitle"]),str(item2["tvSeason"]), str(episode), )
                                                            
    
                    for item in item3:
    
                        if item["lang"]:
                                flag_image = "flags/%s.gif" % (item["lang"],)
                        else:                                                           
                                flag_image = "-.gif"
                        link =  "http://www.podnapisi.net/ppodnapisi/download/i/%s" % (str(item["id"],))
                        rating = int(item['rating'])*2
                        name = item['release']
                        if name == "" : name = title 
                        
                        if item["inexact"]:
                                sync1 = False
                        else:
                                sync1 = True
                                
                                
                        self.subtitles_hash_list.append({'filename':name,'link':link,"language_name":toOpenSubtitles_fromtwo(item["lang"]),"language_flag":flag_image,"language_id":item["lang"],"ID":item["id"],"sync":sync1, "format":"srt", "rating": str(rating) })
    
    
                    self.mergesubtitles()
                    return self.subtitles_list,pod_session
                else:
                    return self.subtitles_list,pod_session

        except :
            return self.subtitles_list,pod_session
        



###-------------------------- Podnapisi By Name -------------################

    def searchsubtitlesbyname_pod( self, name, tvshow, season, episode, lang1, lang2, lang3, year ):
        from xml.dom import minidom
        import urllib
        self.subtitles_name_list = []
        tbsl = "1"
        if len(tvshow) > 1:
            name = tvshow                

        search_url1 = None
        search_url2 = None
        
        name = name.replace(" ","+")
        search_url = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang1)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1"
        
        if lang2!=lang1:
            search_url1 = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang2)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1"
        
        if lang3!=lang1 and lang3!=lang2:
            search_url2 = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang3)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1"
    
        try:
    
            search_url.replace( " ", "+" )
            xbmc.output("%s\nSearching subtitles by name_pod [%s]" % (search_url,name,),level=xbmc.LOGDEBUG )
    
            socket = urllib.urlopen( search_url )
            result = socket.read()
            socket.close()
            xmldoc = minidom.parseString(result)
            
            subtitles = xmldoc.getElementsByTagName("subtitle")
            if search_url1 is not None: 
                socket = urllib.urlopen( search_url1 )
                result = socket.read()
                socket.close()
                xmldoc = minidom.parseString(result)
                subtitles1 = xmldoc.getElementsByTagName("subtitle")
                
                subtitles = subtitles + subtitles1              
            if search_url2 is not None: 
                socket = urllib.urlopen( search_url2 )
                result = socket.read()
                socket.close()
                xmldoc = minidom.parseString(result)
                subtitles1 = xmldoc.getElementsByTagName("subtitle")
                subtitles = subtitles + subtitles1
            if subtitles:
                url_base = "http://www.podnapisi.net/ppodnapisi/download/i/"
    
                for subtitle in subtitles:
                    filename = ""
                    movie = ""
                    lang_name = ""
                    subtitle_id = 0
                    lang_id = ""
                    flag_image = ""
                    link = ""
                    format = "srt"
                    no_files = ""
                    if subtitle.getElementsByTagName("title")[0].firstChild:
                        movie = subtitle.getElementsByTagName("title")[0].firstChild.data
    
                    if subtitle.getElementsByTagName("release")[0].firstChild:
                        filename = subtitle.getElementsByTagName("release")[0].firstChild.data
                        if len(filename) < 2 :
                            filename = "%s (%s)" % (movie,year,)
                    else:
                        filename = "%s (%s)" % (movie,year,) 
    
                    filename = "%s.srt" % (filename,)
                    rating = 0
                    if subtitle.getElementsByTagName("rating")[0].firstChild:
                        rating = subtitle.getElementsByTagName("rating")[0].firstChild.data
                        rating = int(rating)*2                  
                    
    
                    if subtitle.getElementsByTagName("languageName")[0].firstChild:
                        lang_name = subtitle.getElementsByTagName("languageName")[0].firstChild.data
                    
                    if subtitle.getElementsByTagName("id")[0].firstChild:
                        subtitle_id = subtitle.getElementsByTagName("id")[0].firstChild.data
    
                    flag_image = "flags/%s.gif" % ( toOpenSubtitles_two(lang_name), )
    
                    link = "%s%s" % ( url_base,str(subtitle_id), )
    
                    if subtitle.getElementsByTagName("cds")[0].firstChild:
                        no_files = int(subtitle.getElementsByTagName("cds")[0].firstChild.data)
     
                    self.subtitles_name_list.append({'filename':filename,'link':link,'language_name':lang_name,'language_id':lang_id,'language_flag':flag_image,'movie':movie,"ID":subtitle_id,"rating":str(rating),"format":format,"sync":False, "no_files":no_files})
    
                self.mergesubtitles()                  
                return self.subtitles_list
            else:
                return self.subtitles_list

        except :
            return self.subtitles_list
    

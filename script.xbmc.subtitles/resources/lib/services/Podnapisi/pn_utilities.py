# -*- coding: utf-8 -*- 

import sys
import os
import xmlrpclib
from utilities import *
import xbmc
from xml.dom import minidom
import urllib

try:
  # Python 2.6 +
  from hashlib import md5 as md5
  from hashlib import sha256 as sha256
except ImportError:
  # #Python 2.5 and earlier
  from md5 import md5
  import sha256
  
_ = sys.modules[ "__main__" ].__language__
__settings__   = sys.modules[ "__main__" ].__settings__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__


def compare_columns(b,a):
  return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] ) 

class OSDBServer:
  def create(self):
    self.subtitles_hash_list = []
    self.subtitles_list = []
    self.subtitles_name_list = []
 
###-------------------------- Merge Subtitles All -------------################

  def mergesubtitles( self, stack ):
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_name_list ) > 0 ):
      for item in self.subtitles_name_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          if stack:
            if item["no_files"] == 2:
              self.subtitles_list.append( item )
          else:
            if item["no_files"] < 2:
              self.subtitles_list.append( item )                

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list = sorted(self.subtitles_list, compare_columns)


###-------------------------- Podnapisi Hash -------------################


  def searchsubtitles_pod( self, movie_hash, lang1,lang2,lang3, stack):
#      movie_hash = "e1b45885346cfa0b" # Matrix Hash, Debug only
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')      
    pod_session = ""
    hash_pod =[]
    hash_pod.append(movie_hash)      
    lang = []
    lang.append(lang1)
    if lang1!=lang2:
      lang.append(lang2)
    if lang3!=lang2 and lang3!=lang1:
      lang.append(lang3)

    log( __name__ ,"Languages : [%s]" % str(lang))
    log( __name__ ,"Hash : [%s]" % str(hash_pod))
    try:
      user_agent = "%s_v%s" % (__scriptname__.replace(" ","_"),__version__ )
      init = podserver.initiate(user_agent)

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
    
        log( __name__ ,"Auth : [%s]" % str(auth) )                                              
        log( __name__ ,"Filter : [%s]" % str(filt) )
        search = podserver.search(pod_session , hash_pod)
        if str(search['status']) == "200" and len(search['results']) > 0 :
          item2 = search["results"][movie_hash]
          for item in item2["subtitles"]:
            if item["lang"]:
              flag_image = "flags/%s.gif" % (item["lang"],)
            else:                                                           
              flag_image = "-.gif"

            link = str(item["id"])
            if item['release'] == "":
              episode = item2["tvEpisode"]
              if str(episode) == "0":
                name = "%s (%s)" % (str(item2["movieTitle"]),str(item2["movieYear"]),)
              else:
                name = "%s S(%s)E(%s)" % (str(item2["movieTitle"]),str(item2["tvSeason"]), str(episode), )
            else:
              name = item['release']
              
            if item["inexact"]:
              sync1 = False
            else:
              sync1 = True
            self.subtitles_hash_list.append({'filename':name,'link':link,"language_name":twotofull(item["lang"]),"language_flag":flag_image,"language_id":item["lang"],"ID":item["id"],"sync":sync1, "format":"srt", "rating": str(int(item['rating'])*2) })
        self.mergesubtitles(stack)
      return self.subtitles_list,pod_session
    except :
      return self.subtitles_list,pod_session
    



###-------------------------- Podnapisi By Name -------------################

  def searchsubtitlesbyname_pod( self, name, tvshow, season, episode, lang1, lang2, lang3, year, stack ):
    if len(tvshow) > 1:
      name = tvshow                
    search_url1 = None
    search_url2 = None
    name = urllib.quote(name.replace(" ","+"))
    
    search_url = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang1)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1&lang=0"
    log( __name__ ,"%s - Language 1" % search_url)        
    if lang2!=lang1:
      search_url1 = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang2)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1&lang=0"
      log( __name__ ,"%s - Language 2" % search_url1)             
    if lang3!=lang1 and lang3!=lang2:
      search_url2 = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=" + name + "&sJ=" +str(lang3)+ "&sY=" + str(year)+ "&sTS=" + str(season) + "&sTE=" + str(episode) + "&sXML=1&lang=0"
      log( __name__ ,"%s - Language 3" % search_url2)         
    try:
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
        if subtitles1:
          subtitles = subtitles + subtitles1             
      if search_url2 is not None: 
        socket = urllib.urlopen( search_url2 )
        result = socket.read()
        socket.close()
        xmldoc = minidom.parseString(result)
        subtitles1 = xmldoc.getElementsByTagName("subtitle")
        if subtitles1:
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
              filename = "%s (%s).srt" % (movie,year,)
          else:
            filename = "%s (%s).srt" % (movie,year,) 
          rating = 0
          if subtitle.getElementsByTagName("rating")[0].firstChild:
            rating = int(subtitle.getElementsByTagName("rating")[0].firstChild.data)*2
          if subtitle.getElementsByTagName("languageId")[0].firstChild:
            lang_name = onetotwo(subtitle.getElementsByTagName("languageId")[0].firstChild.data)
          if subtitle.getElementsByTagName("id")[0].firstChild:
            subtitle_id = subtitle.getElementsByTagName("id")[0].firstChild.data
          flag_image = "flags/%s.gif" % ( lang_name, )
          link = str(subtitle_id)
          if subtitle.getElementsByTagName("cds")[0].firstChild:
            no_files = int(subtitle.getElementsByTagName("cds")[0].firstChild.data)
          self.subtitles_name_list.append({'filename':filename,'link':link,'language_name':twotofull(lang_name),'language_id':lang_id,'language_flag':flag_image,'movie':movie,"ID":subtitle_id,"rating":str(rating),"format":format,"sync":False, "no_files":no_files})
        self.mergesubtitles(stack)
      return self.subtitles_list
    except :
      return self.subtitles_list
  
  def download(self,pod_session,  id):
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')
    user_agent = "%s_v%s" % (__scriptname__.replace(" ","_"),__version__ )
    init = podserver.initiate(user_agent)
    
    id_pod =[]
    id_pod.append(str(id))    
    username = __settings__.getSetting( "PNuser" )
    password = __settings__.getSetting( "PNpass" )

    hash = md5()
    hash.update(password)
    password = hash.hexdigest()
    password256 = sha256.sha256(str(password) + str(init['nonce'])).hexdigest()
    if str(init['status']) == "200":
      pod_session = init['session']
      auth = podserver.authenticate(pod_session, username, password256)
      if auth['status'] == 300: 
        log( __name__ ,"Authenticate [%s]" % "InvalidCredentials")
      download = podserver.download(pod_session , id_pod)
      if str(download['status']) == "200" and len(download['names']) > 0 :
        download_item = download["names"][0]
        if str(download["names"][0]['id']) == str(id):
          return "http://www.podnapisi.net/static/podnapisi/%s" % download["names"][0]['filename']
          
    return None  
  

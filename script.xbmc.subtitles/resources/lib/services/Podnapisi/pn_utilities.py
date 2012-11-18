# -*- coding: utf-8 -*- 

import sys
import os
import xmlrpclib
from utilities import *
from xml.dom import minidom
import urllib

try:
  # Python 2.6 +
  from hashlib import md5 as md5
  from hashlib import sha256
except ImportError:
  # Python 2.5 and earlier
  from md5 import md5
  from sha256 import sha256
  
__addon__      = sys.modules[ "__main__" ].__addon__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__

USER_AGENT = "%s_v%s" % (__scriptname__.replace(" ","_"),__version__ )

def compare_columns(b,a):
  return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] ) 

class OSDBServer:
  def create(self):
    self.subtitles_hash_list = []
    self.subtitles_list = []
    self.subtitles_name_list = []
 
  def mergesubtitles( self, stack ):
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_name_list ) > 0 ):
      for item in self.subtitles_name_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )                

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list = sorted(self.subtitles_list, compare_columns)

  def searchsubtitles_pod( self, movie_hash, lang1,lang2,lang3, stack):
#    movie_hash = "e1b45885346cfa0b" # Matrix Hash, Debug only
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')      
    pod_session = ""
    hash_pod =[str(movie_hash)]
    lang = []
    lang.append(lang1)
    if lang1!=lang2:
      lang.append(lang2)
    if lang3!=lang2 and lang3!=lang1:
      lang.append(lang3)
    try:
      init = podserver.initiate(USER_AGENT)
      hash = md5()
      hash.update(__addon__.getSetting( "PNpass" ))
      password256 = sha256(str(hash.hexdigest()) + str(init['nonce'])).hexdigest()
      if str(init['status']) == "200":
        pod_session = init['session']
        podserver.authenticate(pod_session, __addon__.getSetting( "PNuser" ), password256)
        podserver.setFilters(pod_session, True, lang , False)
        search = podserver.search(pod_session , hash_pod)
        if str(search['status']) == "200" and len(search['results']) > 0 :
          search_item = search["results"][movie_hash]
          for item in search_item["subtitles"]:
            if item["lang"]:
              flag_image = "flags/%s.gif" % (item["lang"],)
            else:                                                           
              flag_image = "-.gif"
            link = str(item["id"])
            if item['release'] == "":
              episode = search_item["tvEpisode"]
              if str(episode) == "0":
                name = "%s (%s)" % (str(search_item["movieTitle"]),str(search_item["movieYear"]),)
              else:
                name = "%s S(%s)E(%s)" % (str(search_item["movieTitle"]),str(search_item["tvSeason"]), str(episode), )
            else:
              name = item['release']
            if item["inexact"]:
              sync1 = False
            else:
              sync1 = True
            
            self.subtitles_hash_list.append({'filename'      : name,
                                             'link'          : link,
                                             "language_name" : languageTranslate((item["lang"]),2,0),
                                             "language_flag" : flag_image,
                                             "language_id"   : item["lang"],
                                             "ID"            : item["id"],
                                             "sync"          : sync1,
                                             "format"        : "srt",
                                             "rating"        : str(int(item['rating'])*2),
                                             "hearing_imp"   : "n" in item['flags']
                                             })
        self.mergesubtitles(stack)
      return self.subtitles_list,pod_session
    except :
      return self.subtitles_list,pod_session

  def searchsubtitlesbyname_pod( self, name, tvshow, season, episode, lang1, lang2, lang3, year, stack ):
    if len(tvshow) > 1:
      name = tvshow                
    search_url1 = None
    search_url2 = None
    search_url_base = "http://www.podnapisi.net/ppodnapisi/search?tbsl=1&sK=%s&sJ=%s&sY=%s&sTS=%s&sTE=%s&sXML=1&lang=0" % (name.replace(" ","+"), "%s", str(year), str(season), str(episode))
    search_url = search_url_base % str(lang1)
    log( __name__ ,"%s - Language 1" % search_url)        
    if lang2!=lang1:
      search_url1 = search_url_base % str(lang2)
      log( __name__ ,"%s - Language 2" % search_url1)             
    if lang3!=lang1 and lang3!=lang2:
      search_url2 = search_url_base % str(lang3)
      log( __name__ ,"%s - Language 3" % search_url2)         
    try:
      subtitles = self.fetch(search_url)
      if search_url1 is not None: 
        subtitles1 = self.fetch(search_url1)
        if subtitles1:
          subtitles = subtitles + subtitles1             
      if search_url2 is not None: 
        subtitles2 = self.fetch(search_url2)
        if subtitles1:
          subtitles = subtitles + subtitles1
      if subtitles:
        url_base = "http://www.podnapisi.net/ppodnapisi/download/i/"
        for subtitle in subtitles:
          subtitle_id = 0
          rating      = 0
          filename    = ""
          movie       = ""
          lang_name   = ""
          lang_id     = ""
          flag_image  = ""
          link        = ""
          format      = "srt"
          hearing_imp = False
          if subtitle.getElementsByTagName("title")[0].firstChild:
            movie = subtitle.getElementsByTagName("title")[0].firstChild.data
          if subtitle.getElementsByTagName("release")[0].firstChild:
            filename = subtitle.getElementsByTagName("release")[0].firstChild.data
            if len(filename) < 2 :
              filename = "%s (%s).srt" % (movie,year,)
          else:
            filename = "%s (%s).srt" % (movie,year,) 
          if subtitle.getElementsByTagName("rating")[0].firstChild:
            rating = int(subtitle.getElementsByTagName("rating")[0].firstChild.data)*2
          if subtitle.getElementsByTagName("languageId")[0].firstChild:
            lang_name = languageTranslate(subtitle.getElementsByTagName("languageId")[0].firstChild.data, 1,2)
          if subtitle.getElementsByTagName("id")[0].firstChild:
            subtitle_id = subtitle.getElementsByTagName("id")[0].firstChild.data
          if subtitle.getElementsByTagName("flags")[0].firstChild:
              hearing_imp = "n" in subtitle.getElementsByTagName("flags")[0].firstChild.data
          flag_image = "flags/%s.gif" % ( lang_name, )
          link = str(subtitle_id)
          self.subtitles_name_list.append({'filename':filename,
                                           'link':link,
                                           'language_name' : languageTranslate((lang_name),2,0),
                                           'language_id'   : lang_id,
                                           'language_flag' : flag_image,
                                           'movie'         : movie,
                                           "ID"            : subtitle_id,
                                           "rating"        : str(rating),
                                           "format"        : format,
                                           "sync"          : False,
                                           "hearing_imp"   : hearing_imp
                                           })
        self.mergesubtitles(stack)
      return self.subtitles_list
    except :
      return self.subtitles_list
  
  def download(self,pod_session,  id):
    podserver = xmlrpclib.Server('http://ssp.podnapisi.net:8000')  
    init = podserver.initiate(USER_AGENT)
    hash = md5()
    hash.update(__addon__.getSetting( "PNpass" ))
    id_pod =[]
    id_pod.append(str(id))
    password256 = sha256(str(hash.hexdigest()) + str(init['nonce'])).hexdigest()
    if str(init['status']) == "200":
      pod_session = init['session']
      auth = podserver.authenticate(pod_session, __addon__.getSetting( "PNuser" ), password256)
      if auth['status'] == 300: 
        log( __name__ ,"Authenticate [%s]" % "InvalidCredentials")
      download = podserver.download(pod_session , id_pod)
      if str(download['status']) == "200" and len(download['names']) > 0 :
        download_item = download["names"][0]
        if str(download["names"][0]['id']) == str(id):
          return "http://www.podnapisi.net/static/podnapisi/%s" % download["names"][0]['filename']
          
    return None  
  
  def fetch(self,url):
    socket = urllib.urlopen( url )
    result = socket.read()
    socket.close()
    xmldoc = minidom.parseString(result)
    return xmldoc.getElementsByTagName("subtitle")    

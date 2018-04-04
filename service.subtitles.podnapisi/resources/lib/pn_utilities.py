# -*- coding: utf-8 -*- 

import sys
import os
import xmlrpclib
import unicodedata
import struct
from xml.dom import minidom
import urllib, zlib
import xbmc, xbmcvfs

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
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = sys.modules[ "__main__" ].__language__
__scriptid__   = sys.modules[ "__main__" ].__scriptid__

USER_AGENT           = "%s_v%s" % (__scriptname__.replace(" ","_"),__version__ )
SEARCH_URL_IMDB      = "https://www.podnapisi.net/ppodnapisi/search?sI=%s&sJ=%s&sTS=%s&sTE=%s&sXML=1"
SEARCH_URL_IMDB_HASH = "https://www.podnapisi.net/ppodnapisi/search?sI=%s&sJ=%s&sTS=%s&sTE=%s&sMH=%s&sXML=1"
SEARCH_URL           = "https://www.podnapisi.net/ppodnapisi/search?sK=%s&sJ=%s&sY=%s&sTS=%s&sTE=%s&sXML=1"
SEARCH_URL_HASH      = "https://www.podnapisi.net/ppodnapisi/search?sK=%s&sJ=%s&sY=%s&sTS=%s&sTE=%s&sMH=%s&sXML=1"

DOWNLOAD_URL      = "http://www.podnapisi.net/subtitles/%s/download"

LANGUAGES      = (

    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]

    (u"Albanian"                   , "29",       "sq",            "alb",                 "0",                     30201  ),
    (u"Arabic"                     , "12",       "ar",            "ara",                 "1",                     30202  ),
    (u"Belarusian"                 , "0" ,       "hy",            "arm",                 "2",                     30203  ),
    (u"Bosnian"                    , "10",       "bs",            "bos",                 "3",                     30204  ),
    (u"Bulgarian"                  , "33",       "bg",            "bul",                 "4",                     30205  ),
    (u"Catalan"                    , "53",       "ca",            "cat",                 "5",                     30206  ),
    (u"Chinese"                    , "17",       "zh",            "chi",                 "6",                     30207  ),
    (u"Croatian"                   , "38",       "hr",            "hrv",                 "7",                     30208  ),
    (u"Czech"                      , "7",        "cs",            "cze",                 "8",                     30209  ),
    (u"Danish"                     , "24",       "da",            "dan",                 "9",                     30210  ),
    (u"Dutch"                      , "23",       "nl",            "dut",                 "10",                    30211  ),
    (u"English"                    , "2",        "en",            "eng",                 "11",                    30212  ),
    (u"Estonian"                   , "20",       "et",            "est",                 "12",                    30213  ),
    (u"Persian"                    , "52",       "fa",            "per",                 "13",                    30247  ),
    (u"Finnish"                    , "31",       "fi",            "fin",                 "14",                    30214  ),
    (u"French"                     , "8",        "fr",            "fre",                 "15",                    30215  ),
    (u"German"                     , "5",        "de",            "ger",                 "16",                    30216  ),
    (u"Greek"                      , "16",       "el",            "ell",                 "17",                    30217  ),
    (u"Hebrew"                     , "22",       "he",            "heb",                 "18",                    30218  ),
    (u"Hindi"                      , "42",       "hi",            "hin",                 "19",                    30219  ),
    (u"Hungarian"                  , "15",       "hu",            "hun",                 "20",                    30220  ),
    (u"Icelandic"                  , "6",        "is",            "ice",                 "21",                    30221  ),
    (u"Indonesian"                 , "0",        "id",            "ind",                 "22",                    30222  ),
    (u"Italian"                    , "9",        "it",            "ita",                 "23",                    30224  ),
    (u"Japanese"                   , "11",       "ja",            "jpn",                 "24",                    30225  ),
    (u"Korean"                     , "4",        "ko",            "kor",                 "25",                    30226  ),
    (u"Latvian"                    , "21",       "lv",            "lav",                 "26",                    30227  ),
    (u"Lithuanian"                 , "0",        "lt",            "lit",                 "27",                    30228  ),
    (u"Macedonian"                 , "35",       "mk",            "mac",                 "28",                    30229  ),
    (u"Malay"                      , "0",        "ms",            "may",                 "29",                    30248  ),
    (u"Norwegian"                  , "3",        "no",            "nor",                 "30",                    30230  ),
    (u"Polish"                     , "26",       "pl",            "pol",                 "31",                    30232  ),
    (u"Portuguese"                 , "32",       "pt",            "por",                 "32",                    30233  ),
    (u"PortugueseBrazil"           , "48",       "pb",            "pob",                 "33",                    30234  ),
    (u"Romanian"                   , "13",       "ro",            "rum",                 "34",                    30235  ),
    (u"Russian"                    , "27",       "ru",            "rus",                 "35",                    30236  ),
    (u"Serbian"                    , "47",       "sr",            "scc",                 "36",                    30237  ),
    (u"Slovak"                     , "37",       "sk",            "slo",                 "37",                    30238  ),
    (u"Slovenian"                  , "1",        "sl",            "slv",                 "38",                    30239  ),
    (u"Spanish"                    , "28",       "es",            "spa",                 "39",                    30240  ),
    (u"Swedish"                    , "25",       "sv",            "swe",                 "40",                    30242  ),
    (u"Thai"                       , "0",        "th",            "tha",                 "41",                    30243  ),
    (u"Turkish"                    , "30",       "tr",            "tur",                 "42",                    30244  ),
    (u"Ukrainian"                  , "46",       "uk",            "ukr",                 "43",                    30245  ),
    (u"Vietnamese"                 , "51",       "vi",            "vie",                 "44",                    30246  ),
    (u"BosnianLatin"               , "10",       "bs",            "bos",                 "100",                   30204  ),
    (u"Farsi"                      , "52",       "fa",            "per",                 "13",                    30247  ),
    (u"English (US)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    (u"English (UK)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    (u"Portuguese (Brazilian)"     , "48",       "pt-br",         "pob",                 "100",                   30234  ),
    (u"Portuguese (Brazil)"        , "48",       "pb",            "pob",                 "33",                    30234  ),
    (u"Portuguese-BR"              , "48",       "pb",            "pob",                 "33",                    30234  ),
    (u"Brazilian"                  , "48",       "pb",            "pob",                 "33",                    30234  ),
    (u"Español (Latinoamérica)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    (u"Español (España)"           , "28",       "es",            "spa",                 "100",                   30240  ),
    (u"Spanish (Latin America)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    (u"Español"                    , "28",       "es",            "spa",                 "100",                   30240  ),
    (u"SerbianLatin"               , "36",       "sr",            "scc",                 "100",                   30237  ),
    (u"Spanish (Spain)"            , "28",       "es",            "spa",                 "100",                   30240  ),
    (u"Chinese (Traditional)"      , "17",       "zh",            "chi",                 "100",                   30207  ),
    (u"Chinese (Simplified)"       , "17",       "zh",            "chi",                 "100",                   30207  ) )


def languageTranslate(lang, lang_from, lang_to):
  for x in LANGUAGES:
    if lang == x[lang_from] :
      return x[lang_to]

def log(module, msg):
  xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def OpensubtitlesHash(item):
    try:
      if item["rar"]:
        return OpensubtitlesHashRar(item['file_original_path'])
        
      log( __scriptid__,"Hash Standard file")  
      longlongformat = 'q'  # long long
      bytesize = struct.calcsize(longlongformat)
      
      f = xbmcvfs.File(item['file_original_path'])
      filesize = f.size()
      hash = filesize
      
      if filesize < 65536 * 2:
          return "SizeError"
      
      buffer = f.read(65536)
      f.seek(max(0,filesize-65536),0)
      buffer += f.read(65536)
      f.close()
      for x in range((65536/bytesize)*2):
          size = x*bytesize
          (l_value,)= struct.unpack(longlongformat, buffer[size:size+bytesize])
          hash += l_value
          hash = hash & 0xFFFFFFFFFFFFFFFF
      
      returnHash = "%016x" % hash
    except:
      returnHash = "000000000000"

    return returnHash

def OpensubtitlesHashRar(firstrarfile):
    log( __scriptid__,"Hash Rar file")
    f = xbmcvfs.File(firstrarfile)
    a=f.read(4)
    if a!='Rar!':
        raise Exception('ERROR: This is not rar file.')
    seek=0
    for i in range(4):
        f.seek(max(0,seek),0)
        a=f.read(100)        
        type,flag,size=struct.unpack( '<BHH', a[2:2+5]) 
        if 0x74==type:
            if 0x30!=struct.unpack( '<B', a[25:25+1])[0]:
                raise Exception('Bad compression method! Work only for "store".')            
            s_partiizebodystart=seek+size
            s_partiizebody,s_unpacksize=struct.unpack( '<II', a[7:7+2*4])
            if (flag & 0x0100):
                s_unpacksize=(struct.unpack( '<I', a[36:36+4])[0] <<32 )+s_unpacksize
                log( __name__ , 'Hash untested for files biger that 2gb. May work or may generate bad hash.')
            lastrarfile=getlastsplit(firstrarfile,(s_unpacksize-1)/s_partiizebody)
            hash=addfilehash(firstrarfile,s_unpacksize,s_partiizebodystart)
            hash=addfilehash(lastrarfile,hash,(s_unpacksize%s_partiizebody)+s_partiizebodystart-65536)
            f.close()
            return (s_unpacksize,"%016x" % hash )
        seek+=size
    raise Exception('ERROR: Not Body part in rar file.')

def dec2hex(n, l=0):
  # return the hexadecimal string representation of integer n
  s = "%X" % n
  if (l > 0) :
    while len(s) < l:
      s = "0" + s 
  return s

def invert(basestring):
  asal = [basestring[i:i+2]
          for i in range(0, len(basestring), 2)]
  asal.reverse()
  return ''.join(asal)

def calculateSublightHash(filename):

  DATA_SIZE = 128 * 1024;

  if not xbmcvfs.exists(filename) :
    return "000000000000"
  
  fileToHash = xbmcvfs.File(filename)

  if fileToHash.size(filename) < DATA_SIZE :
    return "000000000000"

  sum = 0
  hash = ""
  
  number = 2
  sum = sum + number
  hash = hash + dec2hex(number, 2) 
  
  filesize = fileToHash.size(filename)
  
  sum = sum + (filesize & 0xff) + ((filesize & 0xff00) >> 8) + ((filesize & 0xff0000) >> 16) + ((filesize & 0xff000000) >> 24)
  hash = hash + dec2hex(filesize, 12) 
  
  buffer = fileToHash.read( DATA_SIZE )
  begining = zlib.adler32(buffer) & 0xffffffff
  sum = sum + (begining & 0xff) + ((begining & 0xff00) >> 8) + ((begining & 0xff0000) >> 16) + ((begining & 0xff000000) >> 24)
  hash = hash + invert(dec2hex(begining, 8))

  fileToHash.seek(filesize/2,0)
  buffer = fileToHash.read( DATA_SIZE )
  middle = zlib.adler32(buffer) & 0xffffffff
  sum = sum + (middle & 0xff) + ((middle & 0xff00) >> 8) + ((middle & 0xff0000) >> 16) + ((middle & 0xff000000) >> 24)
  hash = hash + invert(dec2hex(middle, 8))

  fileToHash.seek(filesize-DATA_SIZE,0)
  buffer = fileToHash.read( DATA_SIZE )
  end = zlib.adler32(buffer) & 0xffffffff
  sum = sum + (end & 0xff) + ((end & 0xff00) >> 8) + ((end & 0xff0000) >> 16) + ((end & 0xff000000) >> 24)
  hash = hash + invert(dec2hex(end, 8))
  
  fileToHash.close()
  hash = hash + dec2hex(sum % 256, 2)
  
  return hash.lower()

class PNServer:
  def Create(self):
    self.subtitles_list = []
    self.connected = False
    
  def Login(self):
    # Currently, login is disabled
    return

    self.podserver   = xmlrpclib.Server('http://ssp.podnapisi.net:8000')
    init        = self.podserver.initiate(USER_AGENT)  
    hash        = md5()
    hash.update(__addon__.getSetting( "PNpass" ))
    self.password = sha256(str(hash.hexdigest()) + str(init['nonce'])).hexdigest()
    self.user     = __addon__.getSetting( "PNuser" )
    if init['status'] == 200:
      self.pod_session = init['session']
      auth = self.podserver.authenticate(self.pod_session, self.user, self.password)
      if auth['status'] == 300: 
        log( __scriptid__ ,__language__(32005))
        xbmc.executebuiltin(u'Notification(%s,%s,5000,%s)' %(__scriptname__,
                                                             __language__(32005),
                                                             os.path.join(__cwd__,"icon.png")
                                                            )
                            )
        self.connected = False
      else:
        log( __scriptid__ ,"Connected to Podnapisi server")
        self.connected = True
    else:
      self.connected = False 

  def SearchSubtitlesWeb( self, item):
    def read_subtitles(subtitles):
      for subtitle in subtitles:
        filename    = self.get_element(subtitle, "release")

        if filename == "":
          filename = self.get_element(subtitle, "title")
        
        hashMatch = False
        if (item['OShash'] in self.get_element(subtitle, "exactHashes") or 
           item['SLhash'] in self.get_element(subtitle, "exactHashes")):
          hashMatch = True

        self.subtitles_list.append({'filename'      : filename,
                                    'link'          : self.get_element(subtitle, "pid"),
                                    'movie_id'      : self.get_element(subtitle, "movieId"),
                                    'season'        : self.get_element(subtitle, "tvSeason"),
                                    'episode'       : self.get_element(subtitle, "tvEpisode"),
                                    'language_name' : self.get_element(subtitle, "languageName"),
                                    'language_flag' : self.get_element(subtitle, "language"),
                                    'rating'        : str(int(float(self.get_element(subtitle, "rating")))*2),
                                    'sync'          : hashMatch,
                                    'hearing_imp'   : "n" in self.get_element(subtitle, "flags")
                                    })

    if len(item['tvshow']) > 1:
      item['title'] = item['tvshow']

    selected_languages = ','.join([i for i in item['3let_language'] if isinstance(i, basestring)])

    if (__addon__.getSetting("PNmatch") == 'true'):
      url =  SEARCH_URL_IMDB_HASH % (item['imdb'],
                                    selected_languages,
                                    str(item['season']),
                                    str(item['episode']),
                                    '%s,sublight:%s,sublight:%s' % (item['OShash'],item['SLhash'],md5(item['SLhash']).hexdigest() )
                                    )
      fallback_url =  SEARCH_URL_HASH % (item['title'].replace(" ","+"),
                                         selected_languages,
                                         str(item['year']),
                                         str(item['season']),
                                         str(item['episode']),
                                         '%s,sublight:%s,sublight:%s' % (item['OShash'],item['SLhash'],md5(item['SLhash']).hexdigest() )
                                         )
    else:
      url =  SEARCH_URL_IMDB % (item['imdb'],
                                selected_languages,
                                str(item['season']),
                                str(item['episode'])
                                )
      fallback_url =  SEARCH_URL % (item['title'].replace(" ","+"),
                                   selected_languages,
                                   str(item['year']),
                                   str(item['season']),
                                   str(item['episode'])
                                   )

    if not item.get('imdb'):
      url = fallback_url

    log( __scriptid__ ,"Search URL - %s" % (url))

    subtitles = self.fetch(url)

    if subtitles:
      read_subtitles(subtitles)

    if not self.subtitles_list and url != fallback_url:
      log( __scriptid__ ,"Search - IMDB ID search failed, fallback to title")

      subtitles = self.fetch(fallback_url)

      log( __scriptid__ ,"Search Fallback URL - %s" % (fallback_url))

      if subtitles:
        read_subtitles(subtitles)

    if self.subtitles_list:
      self.mergesubtitles()
    return self.subtitles_list
  
  def Download(self,params):
    print params
    subtitle_ids = []
    # if (__addon__.getSetting("PNmatch") == 'true' and params["hash"] != "000000000000"):
    #   self.Login()
    #   if params["match"] == "True":
    #     subtitle_ids.append(str(params["link"]))

    #   log( __scriptid__ ,"Sending match to Podnapisi server")
    #   result = self.podserver.match(self.pod_session, params["hash"], params["movie_id"], int(params["season"]), int(params["episode"]), subtitle_ids)
    #   if result['status'] == 200:
    #     log( __scriptid__ ,"Match successfuly sent")

    return DOWNLOAD_URL % str(params["link"])

  def get_element(self, element, tag):
    if element.getElementsByTagName(tag)[0].firstChild:
      return element.getElementsByTagName(tag)[0].firstChild.data
    else:
      return ""  

  def fetch(self,url):
    socket = urllib.urlopen( url )
    result = socket.read()
    socket.close()
    xmldoc = minidom.parseString(result)
    return xmldoc.getElementsByTagName("subtitle")    

  def compare_columns(self, b, a):
    return cmp( b["language_name"], a["language_name"] )  or cmp( a["sync"], b["sync"] ) 

  def mergesubtitles(self):
    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list = sorted(self.subtitles_list, self.compare_columns)
       

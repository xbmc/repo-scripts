# -*- coding: utf-8 -*- 

import os
import re
import sys
import xbmc
import xbmcvfs
import xbmcgui
import shutil

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

STATUS_LABEL   = 100
LOADING_IMAGE  = 110
SUBTITLES_LIST = 120
SERVICES_LIST  = 150
CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

SERVICE_DIR    = os.path.join(__cwd__, "resources", "lib", "services")

LANGUAGES      = (
    
    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]
    
    ("Albanian"                   , "29",       "sq",            "alb",                 "0",                     30201  ),
    ("Arabic"                     , "12",       "ar",            "ara",                 "1",                     30202  ),
    ("Belarusian"                 , "0" ,       "hy",            "arm",                 "2",                     30203  ),
    ("Bosnian"                    , "10",       "bs",            "bos",                 "3",                     30204  ),
    ("Bulgarian"                  , "33",       "bg",            "bul",                 "4",                     30205  ),
    ("Catalan"                    , "53",       "ca",            "cat",                 "5",                     30206  ),
    ("Chinese"                    , "17",       "zh",            "chi",                 "6",                     30207  ),
    ("Croatian"                   , "38",       "hr",            "hrv",                 "7",                     30208  ),
    ("Czech"                      , "7",        "cs",            "cze",                 "8",                     30209  ),
    ("Danish"                     , "24",       "da",            "dan",                 "9",                     30210  ),
    ("Dutch"                      , "23",       "nl",            "dut",                 "10",                    30211  ),
    ("English"                    , "2",        "en",            "eng",                 "11",                    30212  ),
    ("Estonian"                   , "20",       "et",            "est",                 "12",                    30213  ),
    ("Persian"                    , "52",       "fa",            "per",                 "13",                    30247  ),
    ("Finnish"                    , "31",       "fi",            "fin",                 "14",                    30214  ),
    ("French"                     , "8",        "fr",            "fre",                 "15",                    30215  ),
    ("German"                     , "5",        "de",            "ger",                 "16",                    30216  ),
    ("Greek"                      , "16",       "el",            "ell",                 "17",                    30217  ),
    ("Hebrew"                     , "22",       "he",            "heb",                 "18",                    30218  ),
    ("Hindi"                      , "42",       "hi",            "hin",                 "19",                    30219  ),
    ("Hungarian"                  , "15",       "hu",            "hun",                 "20",                    30220  ),
    ("Icelandic"                  , "6",        "is",            "ice",                 "21",                    30221  ),
    ("Indonesian"                 , "0",        "id",            "ind",                 "22",                    30222  ),
    ("Italian"                    , "9",        "it",            "ita",                 "23",                    30224  ),
    ("Japanese"                   , "11",       "ja",            "jpn",                 "24",                    30225  ),
    ("Korean"                     , "4",        "ko",            "kor",                 "25",                    30226  ),
    ("Latvian"                    , "21",       "lv",            "lav",                 "26",                    30227  ),
    ("Lithuanian"                 , "0",        "lt",            "lit",                 "27",                    30228  ),
    ("Macedonian"                 , "35",       "mk",            "mac",                 "28",                    30229  ),
    ("Norwegian"                  , "3",        "no",            "nor",                 "29",                    30230  ),
    ("Polish"                     , "26",       "pl",            "pol",                 "30",                    30232  ),
    ("Portuguese"                 , "32",       "pt",            "por",                 "31",                    30233  ),
    ("PortugueseBrazil"           , "48",       "pb",            "pob",                 "32",                    30234  ),
    ("Romanian"                   , "13",       "ro",            "rum",                 "33",                    30235  ),
    ("Russian"                    , "27",       "ru",            "rus",                 "34",                    30236  ),
    ("Serbian"                    , "36",       "sr",            "scc",                 "35",                    30237  ),
    ("Slovak"                     , "37",       "sk",            "slo",                 "36",                    30238  ),
    ("Slovenian"                  , "1",        "sl",            "slv",                 "37",                    30239  ),
    ("Spanish"                    , "28",       "es",            "spa",                 "38",                    30240  ),
    ("Swedish"                    , "25",       "sv",            "swe",                 "39",                    30242  ),
    ("Thai"                       , "0",        "th",            "tha",                 "40",                    30243  ),
    ("Turkish"                    , "30",       "tr",            "tur",                 "41",                    30244  ),
    ("Ukrainian"                  , "46",       "uk",            "ukr",                 "42",                    30245  ),
    ("Vietnamese"                 , "51",       "vi",            "vie",                 "43",                    30246  ),
    ("BosnianLatin"               , "10",       "bs",            "bos",                 "100",                   30204  ),
    ("Farsi"                      , "52",       "fa",            "per",                 "13",                    30247  ),
    ("English (US)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("English (UK)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("Portuguese (Brazilian)"     , "48",       "pt-br",         "pob",                 "100",                   30234  ),
    ("Portuguese (Brazil)"        , "48",       "pb",            "pob",                 "32",                    30234  ),
    ("Portuguese-BR"              , "48",       "pb",            "pob",                 "32",                    30234  ),
    ("Brazilian"                  , "48",       "pb",            "pob",                 "32",                    30234  ),
    ("Español (Latinoamérica)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español (España)"           , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Spanish (Latin America)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español"                    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("SerbianLatin"               , "36",       "sr",            "scc",                 "100",                   30237  ),
    ("Spanish (Spain)"            , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Chinese (Traditional)"      , "17",       "zh",            "chi",                 "100",                   30207  ),
    ("Chinese (Simplified)"       , "17",       "zh",            "chi",                 "100",                   30207  ) )


REGEX_EXPRESSIONS = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09 
                      '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                      '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                      '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                      'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',
                      '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                      '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                 #foo_[s01]_[e01]
                      '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',        #foo, s01e01, foo.s01.e01, foo.s01-e01
                      's([0-9]+)ep([0-9]+)[^\\/]*',                              #foo - s01ep03, foo - s1ep03
                      '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
                     ]



class UserNotificationNotifier:
  def __init__(self, title, initialMessage, time = -1):
    self.__title = title
    xbmc.executebuiltin((u"Notification(%s,%s,%i)" % (title, initialMessage, time)).encode('utf-8'))
    
  def update(self, message, time = -1):
    xbmc.executebuiltin((u"Notification(%s,%s,-1)" % (self.__title, message, time)).encode("utf-8"))

  def close(self, message, time = -1):
    xbmc.executebuiltin((u"Notification(%s,%s,%i)" % (self.__title, message, time)).encode("utf-8")) 

   
def log(module,msg):
  xbmc.log((u"### [%s-%s] - %s" % (__scriptname__,module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

def regex_tvshow(compare, file, sub = ""):
  sub_info = ""
  tvshow = 0
  
  for regex in REGEX_EXPRESSIONS:
    response_file = re.findall(regex, file)                  
    if len(response_file) > 0 : 
      log( __name__ , "Regex File Se: %s, Ep: %s," % (str(response_file[0][0]),str(response_file[0][1]),) )
      tvshow = 1
      if not compare :
        title = re.split(regex, file)[0]
        for char in ['[', ']', '_', '(', ')','.','-']: 
           title = title.replace(char, ' ')
        if title.endswith(" "): title = title[:-1]
        return title,response_file[0][0], response_file[0][1]
      else:
        break
  
  if (tvshow == 1):
    for regex in regex_expressions:       
      response_sub = re.findall(regex, sub)
      if len(response_sub) > 0 :
        try :
          sub_info = "Regex Subtitle Ep: %s," % (str(response_sub[0][1]),)
          if (int(response_sub[0][1]) == int(response_file[0][1])):
            return True
        except: pass      
    return False
  if compare :
    return True
  else:
    return "","",""    

def languageTranslate(lang, lang_from, lang_to):
  for x in LANGUAGES:
    if lang == x[lang_from] :
      return x[lang_to]

def pause():
  if not xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()
    return True
  else:
    return False  
    
def unpause():
  if xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()  

def rem_files(directory):
  try:
    if xbmcvfs.exists(directory):
      shutil.rmtree(directory)
  except:
    pass
    
  if not xbmcvfs.exists(directory):
    os.makedirs(directory)
      
def copy_files( subtitle_file, file_path ):
  subtitle_set = False
  try:
    log( __name__ ,"vfs module copy %s -> %s" % (subtitle_file, file_path))
    xbmcvfs.copy(subtitle_file, file_path)
    subtitle_set = True
  except :
    dialog = xbmcgui.Dialog()
    selected = dialog.yesno( __scriptname__ , _( 748 ), _( 750 ),"" )
    if selected == 1:
      file_path = subtitle_file
      subtitle_set = True

  return subtitle_set, file_path


import sys
import os
import xbmc
import re
import struct


def hashFile(name): 
    try: 
      longlongformat = 'q'  # long long 
      bytesize = struct.calcsize(longlongformat) 
          
      f = open(name, "rb") 
          
      filesize = os.path.getsize(name) 
      hash = filesize 
          
      if filesize < 65536 * 2: 
             return "SizeError" 
       
      for x in range(65536/bytesize): 
              buffer = f.read(bytesize) 
              (l_value,)= struct.unpack(longlongformat, buffer)  
              hash += l_value 
              hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number  
               

      f.seek(max(0,filesize-65536),0) 
      for x in range(65536/bytesize): 
              buffer = f.read(bytesize) 
              (l_value,)= struct.unpack(longlongformat, buffer)  
              hash += l_value 
              hash = hash & 0xFFFFFFFFFFFFFFFF 
       
      f.close() 
      returnedhash =  "%016x" % hash 
      return returnedhash 
    
    except(IOError): 
      return "IOError"


###-------------------------- match sub to file  -------------################        

def regex_tvshow(compare, file, sub = ""):
    regex_expressions = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                        '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09 
                        '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                        '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                        'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',
                        '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                        '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)'                 #foo_[s01]_[e01]
                        '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)'        #foo, s01e01, foo.s01.e01, foo.s01-e01
                        ]
    sub_info = ""
    tvshow = 0
    
    for regex in regex_expressions:
      response_file = re.findall(regex, file)                  
      if len(response_file) > 0 : 
        print "Regex File Se: %s, Ep: %s," % (str(response_file[0][0]),str(response_file[0][1]),)
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




def toOpenSubtitles_two( id ):
  languages = { 
  	"None"                : "none",
    "Albanian"            : "sq",
    "Arabic"              : "ar",
    "Belarusian"          : "hy",
    "Bosnian"             : "bs",
    "BosnianLatin"        : "bs",
    "Bulgarian"           : "bg",
    "Catalan"             : "ca",
    "Chinese"             : "zh",
    "Croatian"            : "hr",
    "Czech"               : "cs",
    "Danish"              : "da",
    "Dutch"               : "nl",
    "English"             : "en",
    "Esperanto"           : "eo",
    "Estonian"            : "et",
    "Farsi"               : "fo",
    "Finnish"             : "fi",
    "French"              : "fr",
    "Galician"            : "gl",
    "Georgian"            : "ka",
    "German"              : "de",
    "Greek"               : "el",
    "Hebrew"              : "he",
    "Hindi"               : "hi",
    "Hungarian"           : "hu",
    "Icelandic"           : "is",
    "Indonesian"          : "id",
    "Italian"             : "it",
    "Japanese"            : "ja",
    "Kazakh"              : "kk",
    "Korean"              : "ko",
    "Latvian"             : "lv",
    "Lithuanian"          : "lt",
    "Luxembourgish"       : "lb",
    "Macedonian"          : "mk",
    "Malay"               : "ms",
    "Norwegian"           : "no",
    "Occitan"             : "oc",
    "Polish"              : "pl",
    "Portuguese"          : "pt",
    "PortugueseBrazil"    : "pb",
    "Brazilian"           : "pb",
    "Romanian"            : "ro",
    "Russian"             : "ru",
    "SerbianLatin"        : "sr",
    "Serbian"             : "sr",
    "Slovak"              : "sk",
    "Slovenian"           : "sl",
    "Spanish"             : "es",
    "Swedish"             : "sv",
    "Syriac"              : "syr",
    "Thai"                : "th",
    "Turkish"             : "tr",
    "Ukrainian"           : "uk",
    "Urdu"                : "ur",
    "Vietnamese"          : "vi",
    "English (US)"        : "en",
    "All"                 : "all"
  }
  return languages[ id ]


        

def twotoone(id):
  languages = {
    "sq"                  :  "29",
    "hy"                  :  "0",
    "ar"                  :  "12",
    "ay"                  :  "0",
    "bs"                  :  "10",
    "pb"                  :  "48",
    "bg"                  :  "33",
    "ca"                  :  "53",
    "zh"                  :  "17",
    "hr"                  :  "38",
    "cs"                  :  "7",
    "da"                  :  "24",
    "nl"                  :  "23",
    "en"                  :  "2",
    "et"                  :  "20",
    "fi"                  :  "31",
    "fr"                  :  "8",
    "de"                  :  "5",
    "el"                  :  "16",
    "he"                  :  "22",
    "hi"                  :  "42",
    "hu"                  :  "15",
    "is"                  :  "6",
    "it"                  :  "9",
    "ja"                  :  "11",
    "kk"                  :  "0",
    "ko"                  :  "4",
    "lv"                  :  "21",
    "mk"                  :  "35",
    "no"                  :  "3",
    "pl"                  :  "26",
    "pt"                  :  "32",
    "ro"                  :  "13",
    "ru"                  :  "27",
    "sr"                  :  "36",
    "sk"                  :  "37",
    "sl"                  :  "1",
    "es"                  :  "28",
    "sv"                  :  "25",
    "th"                  :  "44",
    "tr"                  :  "30",
    "uk"                  :  "46",
    "vi"                  :  "51"
  }
  return languages[ id ]
        

def toOpenSubtitlesId( id ):
  languages = { 
  	"None"                : "none",
    "Albanian"            : "alb",
    "Arabic"              : "ara",
    "Belarusian"          : "arm",
    "Bosnian"             : "bos",
    "BosnianLatin"        : "bos",
    "Bulgarian"           : "bul",
    "Catalan"             : "cat",
    "Chinese"             : "chi",
    "Croatian"            : "hrv",
    "Czech"               : "cze",
    "Danish"              : "dan",
    "Dutch"               : "dut",
    "English"             : "eng",
    "Esperanto"           : "epo",
    "Estonian"            : "est",
    "Farsi"               : "per",
    "Finnish"             : "fin",
    "French"              : "fre",
    "Galician"            : "glg",
    "Georgian"            : "geo",
    "German"              : "ger",
    "Greek"               : "ell",
    "Hebrew"              : "heb",
    "Hindi"               : "hin",
    "Hungarian"           : "hun",
    "Icelandic"           : "ice",
    "Indonesian"          : "ind",
    "Italian"             : "ita",
    "Japanese"            : "jpn",
    "Kazakh"              : "kaz",
    "Korean"              : "kor",
    "Latvian"             : "lav",
    "Lithuanian"          : "lit",
    "Luxembourgish"       : "ltz",
    "Macedonian"          : "mac",
    "Malay"               : "may",
    "Norwegian"           : "nor",
    "Occitan"             : "oci",
    "Polish"              : "pol",
    "Portuguese"          : "por",
    "PortugueseBrazil"    : "pob",
    "Romanian"            : "rum",
    "Russian"             : "rus",
    "SerbianLatin"        : "scc",
    "Serbian"             : "scc",
    "Slovak"              : "slo",
    "Slovenian"           : "slv",
    "Spanish"             : "spa",
    "Swedish"             : "swe",
    "Syriac"              : "syr",
    "Thai"                : "tha",
    "Turkish"             : "tur",
    "Ukrainian"           : "ukr",
    "Urdu"                : "urd",
    "Vietnamese"          : "vie",
    "English (US)"        : "eng",
    "All"                 : "all"
  }
  return languages[ id ]


def toScriptLang(id):
  languages = { 
    "0"                   : "Albanian",
    "1"                   : "Arabic",
    "2"                   : "Belarusian",
    "3"                   : "BosnianLatin",
    "4"                   : "Bulgarian",
    "5"                   : "Catalan",
    "6"                   : "Chinese",
    "7"                   : "Croatian",
    "8"                   : "Czech",
    "9"                   : "Danish",
    "10"                  : "Dutch",
    "11"                  : "English",
    "12"                  : "Estonian",
    "13"                  : "Finnish",
    "14"                  : "French",
    "15"                  : "German",
    "16"                  : "Greek",
    "17"                  : "Hebrew",
    "18"                  : "Hindi",
    "19"                  : "Hungarian",
    "20"                  : "Icelandic",
    "21"                  : "Indonesian",
    "22"                  : "Italian",
    "23"                  : "Japanese",
    "24"                  : "Korean",
    "25"                  : "Latvian",
    "26"                  : "Lithuanian",
    "27"                  : "Macedonian",
    "28"                  : "Norwegian",
    "29"                  : "Polish",
    "30"                  : "Portuguese",
    "31"                  : "PortugueseBrazil",
    "32"                  : "Romanian",
    "33"                  : "Russian",
    "34"                  : "SerbianLatin",
    "35"                  : "Slovak",
    "36"                  : "Slovenian",
    "37"                  : "Spanish",
    "38"                  : "Swedish",
    "39"                  : "Thai",
    "40"                  : "Turkish",
    "41"                  : "Ukrainian",
    "42"                  : "Vietnamese",
  }
  return languages[ id ]       
        
def toSublightLanguage(id):
  languages = { 
  	"0"                   : "None",
    "alb"                 : "Albanian",
    "ara"                 : "Arabic",
    "arm"                 : "Belarusian",
    "bos"                 : "BosnianLatin",
    "bul"                 : "Bulgarian",
    "cat"                 : "Catalan",
    "chi"                 : "Chinese",
    "hrv"                 : "Croatian",
    "cze"                 : "Czech",
    "dan"                 : "Danish",
    "dut"                 : "Dutch",
    "eng"                 : "English",
    "est"                 : "Estonian",
    "fin"                 : "Finnish",
    "fre"                 : "French",
    "ger"                 : "German",
    "ell"                 : "Greek",
    "heb"                 : "Hebrew",
    "hin"                 : "Hindi",
    "hun"                 : "Hungarian",
    "ice"                 : "Icelandic",
    "ind"                 : "Indonesian",
    "ita"                 : "Italian",
    "jpn"                 : "Japanese",
    "kor"                 : "Korean",
    "lav"                 : "Latvian",
    "lit"                 : "Lithuanian",
    "mac"                 : "Macedonian",
    "nor"                 : "Norwegian",
    "pol"                 : "Polish",
    "por"                 : "Portuguese",
    "pob"                 : "PortugueseBrazil",
    "rum"                 : "Romanian",
    "rus"                 : "Russian",
    "scc"                 : "SerbianLatin",
    "slo"                 : "Slovak",
    "slv"                 : "Slovenian",
    "spa"                 : "Spanish",
    "swe"                 : "Swedish",
    "tha"                 : "Thai",
    "tur"                 : "Turkish",
    "ukr"                 : "Ukrainian",
    "vie"                 : "Vietnamese",
  }
  return languages[ id ]
  
def twotofull(id):
  languages = {
            

    "sq"                  :  "Albanian",
    "hy"                  :  "Arabic",
    "bg"                  :  "Bulgarian",
    "zh"                  :  "Chinese",
    "hr"                  :  "Croatian",
    "cs"                  :  "Czech",
    "da"                  :  "Danish",
    "nl"                  :  "Dutch",
    "en"                  :  "English",
    "et"                  :  "Estonian",
    "fi"                  :  "Finnish",
    "fr"                  :  "French",
    "de"                  :  "German",
    "el"                  :  "Greek",
    "he"                  :  "Hebrew",
    "hi"                  :  "Hindi",
    "hu"                  :  "Hungarian",
    "it"                  :  "Italian",
    "ja"                  :  "Japanese",
    "ko"                  :  "Korean",
    "lv"                  :  "Latvian",
    "lt"                  :  "Lithuanian",
    "mk"                  :  "Macedonian",
    "no"                  :  "Norwegian",
    "pl"                  :  "Polish",
    "pt"                  :  "Portuguese",
    "ro"                  :  "Romanian",
    "ru"                  :  "Russian",
    "sr"                  :  "Serbian",
    "sk"                  :  "Slovak",
    "sl"                  :  "Slovenian",
    "es"                  :  "Spanish",
    "sv"                  :  "Swedish",
    "tr"                  :  "Turkish",

  }
  return languages[ id ]  
      

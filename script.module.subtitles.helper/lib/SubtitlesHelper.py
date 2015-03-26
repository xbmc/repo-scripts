# -*- coding: utf-8 -*- 

import os
import zlib
import urllib
import struct
import unicodedata

import xbmc
import xbmcvfs
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

def log(module, msg):
  xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def GetCurrentItem():
  item = {}
  item['temp']               = False
  item['rar']                = False
  item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
  item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
  item['3let_language']      = [] #['scc','eng']
  
  if item['title'] == "":
    log( __scriptid__, "VideoPlayer.OriginalTitle not found")
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
    
  if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
    item['season'] = "0"                                                          #
    item['episode'] = item['episode'][-1:]
  
  if ( item['file_original_path'].find("http") > -1 ):
    item['temp'] = True

  elif ( item['file_original_path'].find("rar://") > -1 ):
    item['rar']  = True
    item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

  elif ( item['file_original_path'].find("stack://") > -1 ):
    stackPath = item['file_original_path'].split(" , ")
    item['file_original_path'] = stackPath[0][8:]

  return item

def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string 
  if len(paramstring)>=2:
    params=paramstring
    cleanedparams=params.replace('?','')
    if (params[len(params)-1]=='/'):
      params=params[0:len(params)-2]
    pairsofparams=cleanedparams.split('&')
    param={}
    for i in range(len(pairsofparams)):
      splitparams={}
      splitparams=pairsofparams[i].split('=')
      if (len(splitparams))==2:
        param[splitparams[0]]=splitparams[1]
                                
  return param

def OpensubtitlesHash(file_path, rar=False):
    try:
      if rar:
        return OpensubtitlesHashRar(file_path)
        
      log( __scriptid__,"Hash Standard file")  
      longlongformat = 'q'  # long long
      bytesize = struct.calcsize(longlongformat)
      
      f = xbmcvfs.File(file_path)
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

def OpensubtitlesHashRar(file_path):
    log( __scriptid__,"Hash Rar file")
    f = xbmcvfs.File(file_path)
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


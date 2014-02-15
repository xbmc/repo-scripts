# -*- coding: utf-8 -*- 

import urllib
import unicodedata

import xbmcaddon
import xbmc

__addon__      = xbmcaddon.Addon()
__version__    = __addon__.getAddonInfo('version') # Module version
__scriptname__ = __addon__.getAddonInfo('name')

def log(module, msg):
    #xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)
    print (u"### [%s] - %s" % (module, msg,)).encode('utf-8')
    
def build_search_string(item):
    if item['mansearch']:
        search_string = urllib.unquote(item['mansearchstr'])
    elif len(item['tvshow']) > 0:
        search_string = ("%s S%.2dE%.2d" % (item['tvshow'],
                                                int(item['season']),
                                                int(item['episode']),)
                                              ).replace(" ","+")      
    else:
        if str(item['year']) == "":
          item['title'], item['year'] = xbmc.getCleanMovieTitle( item['title'] )
    
        search_string = item['title'].replace(" ","+")
    
    log( __name__ , "Search String [ %s ]" % (search_string,)) 
    return search_string
    
    
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')
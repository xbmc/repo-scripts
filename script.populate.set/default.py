
import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import random
import urllib

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

line = sys.argv[0]
title = line.replace("plugin://script.populate.set/,", "", 1)

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__    = __addon__.getLocalizedString

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def fetch_movies():
    if not xbmc.abortRequested:
        json_string = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"field": "set", "operator": "is", "value": "' +title+'"}, "limits": { "start" : 0, "end": 2147483647 },  "properties" : ["title", "fanart", "originaltitle", "studio", "trailer", "director", "year", "genre", "country", "tagline", "plot", "runtime", "file", "plotoutline", "rating", "resume", "art", "streamdetails", "set", "setid", "mpaa", "playcount", "lastplayed"], "sort": { "order": "ascending", "method": "title"} }, "id": "1"}'
        json_query = xbmc.executeJSONRPC('%s' %json_string )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('movies'):
            for item in json_query['result']['movies']:
                if (item['resume']['position'] and item['resume']['total']) > 0:
                    resume = "true"
                    played = '%s%%'%int((float(item['resume']['position']) / float(item['resume']['total'])) * 100)
                else:
                    resume = "false"
                    played = '0%'
                if item['playcount'] >= 1:
                    watched = "true"
                else:
                    watched = "false"
                plot = item['plot']
                art = item['art']
                path = media_path(item['file'])

                play = 'XBMC.RunScript(' + __addonid__ + ',movieid=' + str(item.get('movieid')) + ')'


                # create a list item
                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo( type="Video", infoLabels={ "Title": item['title']})
                liz.setInfo( type="Video", infoLabels={ "Year": item['year']})
                liz.setInfo( type="Video", infoLabels={"Duration": item['runtime']/60})
                liz.setInfo( type="Video", infoLabels={ "Genre": " / ".join(item['genre'])})
                liz.setInfo( type="Video", infoLabels={ "Rating": str(float(item['rating']))})
                liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa']})
                liz.setInfo( type="Video", infoLabels={ "Director": " / ".join(item['director'])})
                liz.setProperty("resumetime", str(item['resume']['position']))
                liz.setProperty("totaltime", str(item['resume']['total']))

                liz.setThumbnailImage(art.get('poster', ''))

                liz.setProperty("fanart_image", art.get('fanart', ''))

                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=item['file'],listitem=liz,isFolder=False)
        del json_query
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

def media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        path = [os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://","").split('%2f/')
        path = []
        for item in temp_path:
            path.append(urllib.url2pathname(item))
    else:
        path = [path]
    return path[0]

log('script version %s started' % __addonversion__)
fetch_movies()
log('script version %s stopped' % __addonversion__)
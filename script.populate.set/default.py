import os
import sys
import xbmc
import xbmcgui
import xbmcaddon
import datetime
import _strptime
import urllib

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

limit = 50
title = sys.argv[ 1 ]
WINDOW = xbmcgui.Window( 10000 )
a = datetime.datetime.now()
json_string = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"field": "set", "operator": "is", "value": "'+title+'"}, "limits": { "start" : 0, "end": 2147483647 },  "properties" : ["title", "director", "year", "genre", "country", "tagline", "plot", "runtime", "file", "plotoutline", "rating", "resume", "art", "streamdetails", "set", "setid", "mpaa"], "sort": { "order": "ascending", "method": "year"} }, "id": "1"}'
json_query = xbmc.executeJSONRPC('%s' %json_string )
json_query = unicode(json_query, 'utf-8', errors='ignore')
json_query = simplejson.loads(json_query)
if json_query.has_key('result') and json_query['result'].has_key('movies'):
    count = 0
    for count in range(int(limit)):
        count += 1
        WINDOW.clearProperty("SetItem.%d.Title" % (count))   
        WINDOW.clearProperty("SetItem.%d.art(poster)" % (count))
        WINDOW.clearProperty("SetItem.%d.Path"    % (count))
        WINDOW.clearProperty("SetItem.%d.Year"    % (count))
        WINDOW.clearProperty("SetItem.%d.Duration"    % (count))
        WINDOW.clearProperty("SetItem.%d.Rating"    % (count))
        WINDOW.clearProperty("SetItem.%d.MPAA"    % (count))
    count = 0
    for item in json_query['result']['movies']:
        set = item['setid']
        setname = item['set']
        if set <> 0:
            try:
                path = os.path.split(item['file'])[0].rsplit(' , ', 1)[1].replace(",,",",")
            except:
                path = os.path.split(item['file'])[0]
            if item['file'].startswith("rar://"):
                path = [os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]]
            elif item['file'].startswith("multipath://"):
                temp_path = path.replace("multipath://","").split('%2f/')
                path = []
                for item in temp_path:
                    path.append(urllib.url2pathname(item))
            else:
                path = item['file']
            art = item['art']
            poster = art.get('poster','')
            count += 1
            WINDOW.setProperty("SetItem.%d.title"          % (count), item['title'])
            WINDOW.setProperty("SetItem.%d.art(poster)"    % (count), poster)
            WINDOW.setProperty("SetItem.%d.Path"    % (count), path)
            WINDOW.setProperty("SetItem.%d.Year"    % (count), str(item['year']))
            WINDOW.setProperty("SetItem.%d.Duration"    % (count), str(int((item['runtime'] / 60) + 0.5)))
            WINDOW.setProperty("SetItem.%d.Rating"    % (count), str(round(float(item['rating']),1)))
            WINDOW.setProperty("SetItem.%d.MPAA"    % (count), item['mpaa'])
            WINDOW.setProperty("SetItem.%d.director"    % (count), " / ".join(item['director']))
    
    WINDOW.setProperty("SetItem.numitems"    , str(count))

del json_query
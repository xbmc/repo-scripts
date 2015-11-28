#!/usr/bin/python
# -*- coding: utf-8 -*-
from resources.lib.PluginContent import *
from resources.lib.SkinShortcutsIntegration import *
enableProfiling = False

class Main:
    
    def __init__(self):
        
        logMsg('started loading pluginentry')
        
        #get params
        params = urlparse.parse_qs(sys.argv[2][1:].decode("utf-8"))
        logMsg("Parameter string: %s" % sys.argv[2])
        
        if params:        
            path=params.get("path",None)
            if path: path = path[0]
            limit=params.get("limit",None)
            if limit: limit = int(limit[0])
            else: limit = 25
            action=params.get("action",None)
            if action: action = action[0].upper()
            refresh=params.get("refresh",None)
            if refresh: refresh = refresh[0].upper()
            optionalParam = None
            imdbid=params.get("imdbid","")
            if imdbid: optionalParam = imdbid[0]
            genre=params.get("genre","")
            if genre: optionalParam = genre[0]
            browse=params.get("browse","")
            if browse: optionalParam = browse[0]
            reversed=params.get("reversed","")
            if reversed: optionalParam = reversed[0]
        
            if action:
                if action == "LAUNCHPVR":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"channelid": %d} } }' %int(path))
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                elif action == "LAUNCH":
                    path = sys.argv[2].split("&path=")[1]
                    xbmc.executebuiltin("Action(Close)")
                    xbmc.executebuiltin(path)
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                elif action == "PLAYALBUM":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(path))
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())

                elif action == "SMARTSHORTCUTS":
                    getSmartShortcuts(path)
                elif action == "BACKGROUNDS":
                    getBackgrounds()
                elif action == "WIDGETS":
                    getWidgets(path)
                elif action == "GETTHUMB":
                    getThumb(path)
                elif action == "EXTRAFANART":
                    getExtraFanArt(path)
                elif action == "WIDGETS":
                    getWidgets(path)
                elif action == "GETCAST":
                    movie=params.get("movie",None)
                    if movie: movie = movie[0]
                    tvshow=params.get("tvshow",None)
                    if tvshow: tvshow = tvshow[0]
                    movieset=params.get("movieset",None)
                    if movieset: movieset = movieset[0]
                    downloadthumbs=params.get("downloadthumbs",False)
                    if downloadthumbs: downloadthumbs = downloadthumbs[0]=="true"
                    getCast(movie,tvshow,movieset,downloadthumbs)
                else:
                    #get a widget listing
                    getPluginListing(action,limit,refresh,optionalParam)
    
        else:
            #do plugin main listing...
            doMainListing()

if (__name__ == "__main__"):
    try:
        if not WINDOW.getProperty("SkinHelper.KodiExit"):
        
            if enableProfiling:
                import cProfile
                import pstats
                import random
                from time import gmtime, strftime
                filename = os.path.join( ADDON_DATA_PATH, strftime( "%Y%m%d%H%M%S",gmtime() ) + "-" + str( random.randrange(0,100000) ) + ".log" )
                cProfile.run( 'Main()', filename )
                stream = open( filename + ".txt", 'w')
                p = pstats.Stats( filename, stream = stream )
                p.sort_stats( "cumulative" )
                p.print_stats()
            else:
                Main()
    except Exception as e:
        logMsg("Error in plugin.py --> " + str(e),0)
logMsg('finished loading pluginentry')

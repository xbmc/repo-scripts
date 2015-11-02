#!/usr/bin/python
# -*- coding: utf-8 -*-

#from resources.lib.Utils import *
from resources.lib.PluginContent import *

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
        
            if action:           
                if action == "NEXTEPISODES":
                    getNextEpisodes(limit)
                if action == "NEXTAIREDTVSHOWS":
                    getNextAiredTvShows(limit)
                elif action == "RECOMMENDEDMOVIES":
                    getRecommendedMovies(limit)
                elif action == "RECOMMENDEDMEDIA":
                    getRecommendedMedia(limit)
                elif action == "RECENTMEDIA":
                    getRecentMedia(limit)
                elif action == "SIMILARMOVIES":
                    imdbid=params.get("imdbid","")
                    if imdbid: imdbid = imdbid[0]
                    getSimilarMovies(limit,imdbid)
                elif action == "SIMILARSHOWS":
                    imdbid=params.get("imdbid","")
                    if imdbid: imdbid = imdbid[0]
                    getSimilarTvShows(limit,imdbid)
                elif action == "MOVIESFORGENRE":
                    getMoviesForGenre(limit)
                elif action == "SHOWSFORGENRE":
                    getShowsForGenre(limit)
                elif action == "INPROGRESSMEDIA":
                    getInProgressMedia(limit) 
                elif action == "INPROGRESSANDRECOMMENDEDMEDIA":
                    getInProgressAndRecommendedMedia(limit)
                elif action == "FAVOURITEMEDIA":
                    getFavouriteMedia(limit)
                elif action == "PVRCHANNELS":
                    getPVRChannels(limit)
                elif action == "PVRCHANNELGROUPS":
                    getPVRChannelGroups(limit)
                elif action == "RECENTALBUMS":
                    browse=params.get("browse","")
                    if browse: browse = browse[0]=="true"
                    else: browse = False
                    getRecentAlbums(limit,browse)
                elif action == "RECOMMENDEDALBUMS":
                    browse=params.get("browse","")
                    if browse: browse = browse[0]=="true"
                    else: browse = False
                    getRecommendedAlbums(limit,browse)
                elif action == "RECOMMENDEDSONGS":
                    getRecommendedSongs(limit)
                elif action == "RECENTSONGS":
                    getRecentSongs(limit)
                elif action == "RECENTPLAYEDALBUMS":
                    browse=params.get("browse","")
                    if browse: browse = browse[0]=="true"
                    else: browse = False
                    getRecentPlayedAlbums(limit,browse)
                elif action == "RECENTPLAYEDSONGS":
                    getRecentPlayedSongs(limit)
                elif action == "PVRRECORDINGS":
                    getPVRRecordings(limit)
                elif action == "FAVOURITES":
                    getFavourites(limit)
                elif action == "SMARTSHORTCUTS":
                    getSmartShortcuts(path)
                elif action == "BACKGROUNDS":
                    getBackgrounds()
                elif action == "WIDGETS":
                    getWidgets(path)
                elif action == "GETTHUMB":
                    getThumb(try_decode(path))
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
                elif action == "LAUNCHPVR":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"channelid": %d} } }' %int(path))
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                elif action == "LAUNCH":
                    path = sys.argv[2].split("&path=")[1]
                    xbmc.executebuiltin(path)
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                elif action == "PLAYALBUM":
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(path))
                    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
    
        else:
            #do plugin main listing...
            doMainListing()

if (__name__ == "__main__"):
    try:
        Main()
    except Exception as e:
        logMsg("Error in plugin.py --> " + str(e),0)
logMsg('finished loading pluginentry')

# -*- coding: utf-8 -*-
from resources.lib.Utils import *

#Kodi contextmenu item to go to the series level from a listing with episodes from multiple shows like in progress, recent etc.
if __name__ == '__main__':
    
    dbId = xbmc.getInfoLabel("ListItem.DBID")
    if not dbId or dbId == "-1":
        dbId = xbmc.getInfoLabel("ListItem.Property(DBID)")
        
    if dbId:
        logMsg("Context menu open series level for episodeId " + dbId)
        json_result = getJSON('VideoLibrary.GetEpisodeDetails','{ "episodeid": %d, "properties": [ "tvshowid" ] }' %(int(dbId)))
        if json_result:
            path = "videodb://tvshows/titles/%s/" %str(json_result["tvshowid"])
            xbmc.executebuiltin("ActivateWindow(Video,%s,return)" %path)
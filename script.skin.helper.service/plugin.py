#!/usr/bin/python
# -*- coding: utf-8 -*-
import resources.lib.PluginContent as plugincontent
import resources.lib.Utils as utils
import resources.lib.SkinShortcutsIntegration as skinshortcuts
import urlparse
import xbmc,xbmcgui,xbmcplugin
enableProfiling = False

class Main:
    
    def __init__(self):
        
        utils.logMsg('started loading pluginentry')
        
        #get params
        action = None
        params = urlparse.parse_qs(sys.argv[2][1:].decode("utf-8"))
        utils.logMsg("Parameter string: %s" % sys.argv[2])
        
        if params:        
            path=params.get("path",None)
            if path: path = path[0]
            limit=params.get("limit",None)
            if limit: limit = int(limit[0])
            else: limit = 25
            action=params.get("action",None)
            if action: action = action[0].upper()
        
        if action:
            if action == "LAUNCHPVR":
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"channelid": %d} } }' %int(path))
            if action == "PLAYRECORDING":
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                #retrieve the recording and play as listitem to get resume working
                json_result = utils.getJSON('PVR.GetRecordingDetails', '{"recordingid": %d, "properties": [ %s ]}' %(int(path),plugincontent.fields_pvrrecordings))
                if json_result:
                    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "recordingid": %d } }, "id": 1 }' % int(path))
                    if json_result["resume"].get("position"):
                        for i in range(25):
                            if xbmc.getCondVisibility("Player.HasVideo"):
                                break
                            xbmc.sleep(250)
                        xbmc.Player().seekTime(json_result["resume"].get("position"))
            elif action == "LAUNCH":
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                path = sys.argv[2].split("&path=")[1]
                xbmc.sleep(150)
                xbmc.executebuiltin(path)
            elif action == "PLAYALBUM":
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
                xbmc.sleep(150)
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(path))
            elif action == "SMARTSHORTCUTS":
                skinshortcuts.getSmartShortcuts(path)
            elif action == "BACKGROUNDS":
                skinshortcuts.getBackgrounds()
            elif action == "WIDGETS":
                skinshortcuts.getWidgets(path)
            elif action == "GETTHUMB":
                plugincontent.getThumb(path)
            elif action == "EXTRAFANART":
                plugincontent.getExtraFanArt(path)
            elif action == "GETCAST":
                movie=params.get("movie",None)
                if movie: movie = movie[0]
                tvshow=params.get("tvshow",None)
                if tvshow: tvshow = tvshow[0]
                movieset=params.get("movieset",None)
                if movieset: movieset = movieset[0]
                episode=params.get("episode",None)
                if episode: episode = episode[0]
                downloadthumbs=params.get("downloadthumbs",False)
                if downloadthumbs: downloadthumbs = downloadthumbs[0]=="true"
                plugincontent.getCast(movie,tvshow,movieset,episode,downloadthumbs)
            elif action == "ALPHABET":
                allLetters = []
                if xbmc.getInfoLabel("Container.NumItems"):
                    for i in range(int(xbmc.getInfoLabel("Container.NumItems"))):
                        allLetters.append(xbmc.getInfoLabel("Listitem(%s).SortLetter"%i).upper())
                    
                    startNumber = ""
                    for number in ["2","3","4","5","6","7","8","9"]:
                        if number in allLetters:
                            startNumber = number
                            break
                    
                    for letter in [startNumber,"A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]:
                        if letter == startNumber:
                            label = "#"
                        else: label = letter
                        li = xbmcgui.ListItem(label=label)
                        if not letter in allLetters:
                            path = "noop"
                            li.setProperty("NotAvailable","true")
                        else:
                            path = "plugin://script.skin.helper.service/?action=alphabetletter&letter=%s" %letter
                        xbmcplugin.addDirectoryItem(int(sys.argv[1]), path, li)
                xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            elif action == "ALPHABETLETTER":
                letter=params.get("letter",None)
                if letter: 
                    letter = letter[0]
                    if letter in ["A", "B", "C", "2"]:
                        jumpcmd = "2"
                    elif letter in ["D", "E", "F", "3"]:
                        jumpcmd = "3"
                    elif letter in ["G", "H", "I", "4"]:
                        jumpcmd = "4"
                    elif letter in ["J", "K", "L", "5"]:
                        jumpcmd = "5"
                    elif letter in ["M", "N", "O", "6"]:
                        jumpcmd = "6"
                    elif letter in ["P", "Q", "R", "S", "7"]:
                        jumpcmd = "7"
                    elif letter in ["T", "U", "V", "8"]:
                        jumpcmd = "8"
                    elif letter in ["W", "X", "Y", "Z", "9"]:
                        jumpcmd = "9"
                    else:
                        return

                    xbmc.executebuiltin("SetFocus(50)")
                    for i in range(6):
                        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Input.ExecuteAction", "params": { "action": "jumpsms%s" }, "id": 1 }' % (jumpcmd))
                        xbmc.sleep(50)
                        if xbmc.getInfoLabel("ListItem.Sortletter").upper() == letter:
                            break

            else:
                #get a widget listing
                refresh=params.get("reload",None)
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
                type=params.get("type","")
                if type: optionalParam = type[0]
                name=params.get("name","")
                if name: optionalParam = name[0]
                randomize=params.get("randomize","")
                if randomize: randomize = randomize[0]
                randomize = randomize == "true"
                plugincontent.getPluginListing(action,limit,refresh,optionalParam,randomize)

        else:
            #do plugin main listing...
            plugincontent.doMainListing()

if (__name__ == "__main__"):
    try:
        if utils.WINDOW.getProperty("SkinHelperShutdownRequested"):
            utils.logMsg("plugin.py --> Not forfilling request: Kodi is exiting" ,0)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        elif enableProfiling:
            import cProfile
            import pstats
            import random
            from time import gmtime, strftime
            filename = os.path.join( ADDON_DATA_PATH, strftime( "%Y%m%d%H%M%S",gmtime() ) + "-" + str( random.randrange(0,100000) ) + ".log" )
            cProfile.run( 'Main()', filename )
            with open( filename + ".txt", 'w') as stream:
                stream.write(sys.argv[2])
                p = pstats.Stats( filename, stream = stream )
                p.sort_stats( "cumulative" )
                p.print_stats()
        else:
            Main()
    except Exception as e:
        utils.logMsg("Error in plugin.py --> " + str(e),0)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
utils.logMsg('finished loading pluginentry')

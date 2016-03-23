#!/usr/bin/python
# -*- coding: utf-8 -*-

import urlparse
import xbmc,xbmcgui,xbmcplugin,xbmcvfs
try:
    import resources.lib.MainModule as mainmodule
    import resources.lib.Utils as utils
except:
    xbmcgui.Dialog().ok(heading="Skin Helper Service", line1="Installation is missing files. Please reinstall the skin helper service addon to fix this issue.")

class Main:
    
    def getParams(self):
        #extract the params from the called script path
        params = {}
        for arg in sys.argv:
            if arg == 'script.skin.helper.service' or arg == 'default.py':
                continue
            arg = arg.replace('"', '').replace("'", " ").replace("?", "")
            if "=" in arg:
                paramname = arg.split('=')[0].upper()
                paramvalue = arg.split('=')[1]
                params[paramname] = paramvalue
        
        utils.logMsg("Parameter string: " + str(params))
        return params
    
    def __init__(self):
        
        utils.logMsg('started loading script entry')
        params = self.getParams()
        
        if params:
            action = params.get("ACTION","").upper()

            if action =="ADDSHORTCUT":
                mainmodule.addShortcutWorkAround()
            
            elif action == "MUSICSEARCH":
                mainmodule.musicSearch()
            
            elif action == "SETVIEW":
                mainmodule.setView()
            
            elif action == "SEARCHYOUTUBE":
                title = params.get("TITLE",None)
                windowHeader = params.get("HEADER","")
                autoplay = params.get("AUTOPLAY","")
                windowed = params.get("WINDOWED","")
                mainmodule.searchYouTube(title,windowHeader,autoplay,windowed)
            
            elif action == "SETFOCUS":
                control = params.get("CONTROL",None)
                xbmc.sleep(50)
                xbmc.executebuiltin("Control.SetFocus(%s)"%control)
            
            elif action == "SETFORCEDVIEW":
                contenttype = params.get("CONTENTTYPE",None)
                mainmodule.setForcedView(contenttype)
                
            elif action == "SETSKINSETTING":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                mainmodule.setSkinSetting(setting,windowHeader)
                
            elif action == "SETSKINCONSTANT":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                mainmodule.setSkinConstant(setting,windowHeader)
                
            elif action == "SETSKINSHORTCUTSPROPERTY":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                property = params.get("PROPERTY","")
                mainmodule.setSkinShortCutsProperty(setting,windowHeader,property)
            
            elif action == "TOGGLEKODISETTING":
                kodisetting = params.get("SETTING")
                mainmodule.toggleKodiSetting(kodisetting)
            
            elif action == "ENABLEVIEWS":
                mainmodule.enableViews()
                
            elif action == "SPLASHSCREEN":
                file = params.get("FILE","")
                duration = params.get("DURATION","")
                if duration:
                    mainmodule.show_splash(file,int(duration))
                else:
                    mainmodule.show_splash(file)
            
            elif action == "VIDEOSEARCH":
                from resources.lib.SearchDialog import SearchDialog
                searchDialog = SearchDialog("script-skin_helper_service-CustomSearch.xml", utils.ADDON_PATH, "Default", "1080i")
                searchDialog.doModal()
                resultAction = searchDialog.action
                del searchDialog
                if resultAction:
                    if "jsonrpc" in resultAction:
                        xbmc.executeJSONRPC(resultAction)
                    else:
                        xbmc.executebuiltin(resultAction)
            
            elif action == "SHOWINFO":
                xbmc.executebuiltin( "ActivateWindow(busydialog)" )
                from resources.lib.InfoDialog import GUI
                item = None
                if params.get("MOVIEID"):
                    item = utils.getJSON('VideoLibrary.GetMovieDetails', '{ "movieid": %s, "properties": [ %s ] }' %(params.get("MOVIEID"),utils.fields_movies))
                    content = "movies"
                elif params.get("EPISODEID"):
                    item = utils.getJSON('VideoLibrary.GetEpisodeDetails', '{ "episodeid": %s, "properties": [ %s ] }' %(params.get("EPISODEID"),utils.fields_episodes))
                    content = "episodes"
                elif params.get("TVSHOWID"):
                    item = utils.getJSON('VideoLibrary.GetTVShowDetails', '{ "tvshowid": %s, "properties": [ %s ] }' %(params.get("TVSHOWID"),utils.fields_tvshows))
                    content = "tvshows"
                if item:
                    liz = utils.prepareListItem(item)
                    liz = utils.createListItem(item)
                    liz.setProperty("json",repr(item))
                    info_dialog = GUI( "script-skin_helper_service-CustomInfo.xml" , utils.ADDON_PATH, "Default", "1080i", listitem=liz, content=content )
                    info_dialog.doModal()
                    resultAction = info_dialog.action
                    del info_dialog
                    if resultAction:
                        if "jsonrpc" in resultAction:
                            xbmc.executeJSONRPC(resultAction)
                        else:
                            xbmc.executebuiltin(resultAction)
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            
            elif action == "COLORPICKER":
                from resources.lib.ColorPicker import ColorPicker
                colorPicker = ColorPicker("script-skin_helper_service-ColorPicker.xml", utils.ADDON_PATH, "Default", "1080i")
                colorPicker.skinString = params.get("SKINSTRING","")
                colorPicker.winProperty = params.get("WINPROPERTY","")
                colorPicker.activePalette = params.get("PALETTE","")
                colorPicker.headerLabel = params.get("HEADER","")
                propname = params.get("SHORTCUTPROPERTY","")
                colorPicker.shortcutProperty = propname
                colorPicker.doModal()
                if propname and not isinstance(colorPicker.result, int):
                    mainmodule.waitForSkinShortcutsWindow()
                    xbmc.sleep(400)
                    currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowDialogId() )
                    currentWindow.setProperty("customProperty",propname)
                    currentWindow.setProperty("customValue",colorPicker.result[0])
                    xbmc.executebuiltin("SendClick(404)")
                    xbmc.sleep(250)
                    currentWindow.setProperty("customProperty",propname+".name")
                    currentWindow.setProperty("customValue",colorPicker.result[1])
                    xbmc.executebuiltin("SendClick(404)")
                del colorPicker
            
            elif action == "COLORTHEMES":
                from resources.lib.ColorThemes import ColorThemes
                colorThemes = ColorThemes("DialogSelect.xml", utils.ADDON_PATH)
                colorThemes.daynight = params.get("DAYNIGHT",None)
                colorThemes.doModal()
                del colorThemes
            
            elif action == "CONDITIONALBACKGROUNDS":
                from resources.lib.ConditionalBackgrounds import ConditionalBackgrounds
                conditionalBackgrounds = ConditionalBackgrounds("DialogSelect.xml", utils.ADDON_PATH)
                conditionalBackgrounds.doModal()
                del conditionalBackgrounds
            
            elif action == "CREATECOLORTHEME":
                import resources.lib.ColorThemes as colorThemes
                colorThemes.createColorTheme()
            
            elif action == "RESTORECOLORTHEME":
                import resources.lib.ColorThemes as colorThemes
                colorThemes.restoreColorTheme()
            
            elif action == "OVERLAYTEXTURE":    
                mainmodule.selectOverlayTexture()
            
            elif action == "BUSYTEXTURE":    
                mainmodule.selectBusyTexture()
                
            elif action == "CACHEALLMUSICART": 
                import resources.lib.ArtworkUtils as artworkutils
                artworkutils.preCacheAllMusicArt()

            elif action == "RESETCACHE":
                path = params.get("PATH")
                if path == "pvr":
                    path = utils.WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")
                    utils.WINDOW.setProperty("resetPvrArtCache","reset")
                elif path == "music":
                    path = "special://profile/addon_data/script.skin.helper.service/musicart/"
                    utils.WINDOW.setProperty("resetMusicArtCache","reset")
                elif path == "wallbackgrounds":
                    path = "special://profile/addon_data/script.skin.helper.service/wallbackgrounds/"
                    utils.WINDOW.setProperty("resetWallArtCache","reset")
                else: path = None
                
                if path:
                    success = True
                    ret = xbmcgui.Dialog().yesno(heading=utils.ADDON.getLocalizedString(32089), line1=utils.ADDON.getLocalizedString(32090)+path)
                    if ret:
                        success = utils.recursiveDelete(path)
                        if success:
                            xbmcgui.Dialog().ok(heading=utils.ADDON.getLocalizedString(32089), line1=utils.ADDON.getLocalizedString(32091))
                        else:
                            xbmcgui.Dialog().ok(heading=utils.ADDON.getLocalizedString(32089), line1=utils.ADDON.getLocalizedString(32092))
                    
            elif action == "BACKUP":
                import resources.lib.BackupRestore as backup
                filter = params.get("FILTER","")
                silent = params.get("SILENT",None)
                promptfilename = params.get("PROMPTFILENAME","false")
                backup.backup(filter,silent,promptfilename.lower())
            
            elif action == "RESTORE":
                import resources.lib.BackupRestore as backup
                silent = params.get("SILENT",None)
                backup.restore(silent)
            
            elif action == "RESET":
                import resources.lib.BackupRestore as backup
                filter = params.get("FILTER","")
                silent = params.get("SILENT","") == "true"
                backup.reset(filter,silent)
                xbmc.Monitor().waitForAbort(2)
                mainmodule.correctSkinSettings()
            
            elif action == "DIALOGOK":
                headerMsg = params.get("HEADER")
                bodyMsg = params.get("MESSAGE")
                if bodyMsg.startswith(" "): bodyMsg = bodyMsg[1:]
                if headerMsg.startswith(" "): headerMsg = headerMsg[1:]
                xbmcgui.Dialog().ok(heading=headerMsg, line1=bodyMsg)
                
            elif action == "DIALOGYESNO":
                headerMsg = params.get("HEADER")
                bodyMsg = params.get("MESSAGE")
                yesactions = params.get("YESACTION","").split("|")
                noactions = params.get("NOACTION","").split("|")
                if bodyMsg.startswith(" "): bodyMsg = bodyMsg[1:]
                if headerMsg.startswith(" "): headerMsg = headerMsg[1:]
                if xbmcgui.Dialog().yesno(heading=headerMsg, line1=bodyMsg):
                    for action in yesactions:
                        xbmc.executebuiltin(action.encode("utf-8"))
                else:
                    for action in noactions:
                        xbmc.executebuiltin(action.encode("utf-8"))
                
            elif action == "TEXTVIEWER":
                headerMsg = params.get("HEADER","")
                bodyMsg = params.get("MESSAGE","")
                if bodyMsg.startswith(" "): bodyMsg = bodyMsg[1:]
                if headerMsg.startswith(" "): headerMsg = headerMsg[1:]
                xbmcgui.Dialog().textviewer(headerMsg, bodyMsg)

            elif action == "FILEEXISTS":
                filename = params.get("FILE")
                skinstring = params.get("SKINSTRING")
                windowprop = params.get("WINDOWPROP")
                if xbmcvfs.exists(filename):
                    if windowprop:
                        utils.WINDOW.setProperty(windowprop,"exists")
                    if skinstring:
                        xbmc.executebuiltin("Skin.SetString(%s,exists)" %skinstring)
                else:
                    if windowprop:
                        utils.WINDOW.clearProperty(windowprop)
                    if skinstring:
                        xbmc.executebuiltin("Skin.Reset(%s)" %skinstring)
            
            elif action == "STRIPSTRING":
                splitchar = params.get("SPLITCHAR")
                string = params.get("STRING")
                output = params.get("OUTPUT")
                index = params.get("INDEX",0)
                string = string.split(splitchar)[int(index)]
                utils.WINDOW.setProperty(output, string)
                
            elif action == "GETPLAYERFILENAME":
                output = params.get("OUTPUT")
                filename = xbmc.getInfoLabel("Player.FileNameAndPath")
                if not filename: filename = xbmc.getInfoLabel("Player.FileName")
                if "filename=" in filename:
                    url_params = dict(urlparse.parse_qsl(filename))
                    filename = url_params.get("filename")
                utils.WINDOW.setProperty(output, filename)
                
            elif action == "GETFILENAME":
                output = params.get("OUTPUT")
                filename = xbmc.getInfoLabel("ListItem.FileNameAndPath")
                if not filename: filename = xbmc.getInfoLabel("ListItem.FileName")
                if not filename: filename = xbmc.getInfoLabel("Container(999).ListItem.FileName")
                if not filename: filename = xbmc.getInfoLabel("Container(999).ListItem.FileNameAndPath")
                if "filename=" in filename:
                    url_params = dict(urlparse.parse_qsl(filename))
                    filename = url_params.get("filename")
                utils.WINDOW.setProperty(output, filename)
                
            elif action == "CHECKRESOURCEADDONS":
                ADDONSLIST = params.get("ADDONSLIST")
                mainmodule.checkResourceAddons(ADDONSLIST)



if (__name__ == "__main__"):
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    if not utils.WINDOW.getProperty("SkinHelperShutdownRequested"):
        Main()
    
utils.logMsg('finished loading script entry')

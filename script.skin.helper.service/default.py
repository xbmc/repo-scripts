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
            arg = arg.decode("utf-8")
            if arg == 'script.skin.helper.service' or arg == 'default.py':
                continue
            elif "=" in arg:
                paramname = arg.split('=')[0]
                paramvalue = arg.replace(paramname+"=","")
                params[paramname] = paramvalue
                params[paramname.upper()] = paramvalue
        
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
                fallback = params.get("FALLBACK",None)
                count = 0
                while not xbmc.getCondVisibility("Control.HasFocus(%s)" %control):
                    if count == 20 or (fallback and xbmc.getCondVisibility("Control.IsVisible(%s) + !IntegerGreaterThan(Container(%s).NumItems,0)" %(control,control))):
                        if fallback: xbmc.executebuiltin("Control.SetFocus(%s)"%fallback)
                        break
                    else:
                        xbmc.executebuiltin("Control.SetFocus(%s)"%control)
                        xbmc.sleep(50)
                        count += 1
                
            elif action == "SETFORCEDVIEW":
                contenttype = params.get("CONTENTTYPE",None)
                mainmodule.setForcedView(contenttype)

            elif action == "SAVESKINIMAGE":
                skinstring = params.get("SKINSTRING","")
                windowHeader = params.get("HEADER","")
                multi = params.get("MULTI","") == "true"
                mainmodule.saveSkinImage(skinstring,multi,windowHeader)
            
            elif action == "SETSKINSETTING":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                originalId = params.get("ID","")
                mainmodule.setSkinSetting(setting=setting,windowHeader=windowHeader,originalId=originalId)
                
            elif action == "SETSKINCONSTANT":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                value = params.get("VALUE","")
                mainmodule.setSkinConstant(setting,windowHeader,value)
                
            elif action == "SETSKINCONSTANTS":
                settings = params.get("SETTINGS","").split("|")
                values = params.get("VALUES","").split("|")
                mainmodule.setSkinConstant(settings,values)
                
            elif action == "SETSKINSHORTCUTSPROPERTY":
                setting = params.get("SETTING","")
                windowHeader = params.get("HEADER","")
                property = params.get("PROPERTY","")
                mainmodule.setSkinShortCutsProperty(setting,windowHeader,property)
            
            elif action == "TOGGLEKODISETTING":
                kodisetting = params.get("SETTING")
                mainmodule.toggleKodiSetting(kodisetting)
                
            elif action == "SETKODISETTING":
                kodisetting = params.get("SETTING")
                value = params.get("VALUE")
                mainmodule.setKodiSetting(kodisetting,value)
            
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
                
                #try to figure out the params automatically if no ID provided...
                if not ( params.get("MOVIEID") or params.get("EPISODEID") or params.get("TVSHOWID") ):
                    widgetContainer = utils.WINDOW.getProperty("SkinHelper.WidgetContainer").decode('utf-8')
                    if widgetContainer: widgetContainerPrefix = "Container(%s)."%widgetContainer
                    else: widgetContainerPrefix = ""
                    dbid = xbmc.getInfoLabel("%sListItem.DBID"%widgetContainerPrefix).decode('utf-8')
                    if not dbid or dbid == "-1": dbid = xbmc.getInfoLabel("%sListItem.Property(DBID)"%widgetContainerPrefix).decode('utf-8')
                    if dbid == "-1": dbid = ""
                    dbtype = xbmc.getInfoLabel("%sListItem.DBTYPE"%widgetContainerPrefix).decode('utf-8')
                    utils.logMsg("dbtype: %s - dbid: %s" %(dbtype,dbid))
                    if not dbtype: dbtype = xbmc.getInfoLabel("%sListItem.Property(DBTYPE)"%widgetContainerPrefix).decode('utf-8')
                    if not dbtype:
                        db_type = xbmc.getInfoLabel("%sListItem.Property(type)"%widgetContainerPrefix).decode('utf-8')
                        if "episode" in db_type.lower() or xbmc.getLocalizedString(20360).lower() in db_type.lower(): dbtype = "episode"
                        elif "movie" in db_type.lower() or xbmc.getLocalizedString(342).lower() in db_type.lower(): dbtype = "movie"
                        elif "tvshow" in db_type.lower() or xbmc.getLocalizedString(36903).lower() in db_type.lower(): dbtype = "tvshow"
                        elif "album" in db_type.lower() or xbmc.getLocalizedString(558).lower() in db_type.lower(): dbtype = "album"
                        elif "song" in db_type.lower() or xbmc.getLocalizedString(36920).lower() in db_type.lower(): dbtype = "song"
                    if dbid and dbtype: params["%sID" %dbtype.upper()] = dbid
                    params["lastwidgetcontainer"] = widgetContainer
                
                #open info dialog...
                from resources.lib.InfoDialog import GUI
                info_dialog = GUI( "script-skin_helper_service-CustomInfo.xml" , utils.ADDON_PATH, "Default", "1080i", params=params )
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                if info_dialog.listitem:
                    info_dialog.doModal()
                    resultAction = info_dialog.action
                    if resultAction:
                        while xbmc.getCondVisibility("System.HasModalDialog | Window.IsActive(script-ExtendedInfo Script-DialogVideoInfo.xml) | Window.IsActive(script-ExtendedInfo Script-DialogInfo.xml) | Window.IsActive(script-skin_helper_service-CustomInfo.xml) | Window.IsActive(script-skin_helper_service-CustomSearch.xml)"):
                            xbmc.executebuiltin("Action(Back)")
                            xbmc.sleep(500)
                        if "jsonrpc" in resultAction:
                            xbmc.executeJSONRPC(resultAction)
                        else:
                            xbmc.executebuiltin(resultAction)
                
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
                    path = "special://profile/addon_data/script.skin.helper.service/musicartcache/"
                    utils.WINDOW.setProperty("resetMusicArtCache","reset")
                elif path == "wallbackgrounds":
                    path = "special://profile/addon_data/script.skin.helper.service/wallbackgrounds/"
                    utils.WINDOW.setProperty("resetWallArtCache","reset")
                else: path = None
                
                if path:
                    success = True
                    ret = xbmcgui.Dialog().yesno(heading=utils.ADDON.getLocalizedString(32089), line1=utils.ADDON.getLocalizedString(32090)+path)
                    if ret:
                        utils.WINDOW.setProperty("SkinHelper.IgnoreCache","ignore")
                        success = utils.recursiveDelete(path)
                        if success:
                            utils.checkFolders()
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
                
            elif action == "GETPERCENTAGE":
                total = int(params.get("TOTAL"))
                count = int(params.get("COUNT"))
                roundsteps = params.get("ROUNDSTEPS")
                skinstring = params.get("SKINSTRING")
                
                percentage = int(round((1.0 * count / total) * 100))
                if roundsteps:
                    roundsteps = int(roundsteps)
                    percentage = percentage + (roundsteps - percentage) % roundsteps
                
                xbmc.executebuiltin("Skin.SetString(%s,%s)" %(skinstring,percentage))    


if (__name__ == "__main__"):
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    if not utils.WINDOW.getProperty("SkinHelperShutdownRequested"):
        Main()
    
utils.logMsg('finished loading script entry')

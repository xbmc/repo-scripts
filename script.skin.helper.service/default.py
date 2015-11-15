#!/usr/bin/python
# -*- coding: utf-8 -*-

#from resources.lib.Utils import *
from resources.lib.MainModule import *

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
        
        logMsg("Parameter string: " + str(params))
        return params
    
    def __init__(self):
        
        logMsg('started loading script entry')
        params = self.getParams()
        
        if params:
            action = params.get("ACTION","").upper()

            if action =="ADDSHORTCUT":
                addShortcutWorkAround()
            
            elif action == "MUSICSEARCH":
                musicSearch()
            
            elif action == "SETVIEW":
                setView()
            
            elif action == "SEARCHYOUTUBE":
                title = params.get("TITLE",None)
                windowHeader = params.get("HEADER","")
                searchYouTube(title,windowHeader)
            
            elif action == "SETFOCUS":
                control = params.get("CONTROL",None)
                xbmc.sleep(50)
                xbmc.executebuiltin("Control.SetFocus(%s)"%control)
            
            elif action == "SETFORCEDVIEW":
                contenttype = params.get("CONTENTTYPE",None)
                setForcedView(contenttype)
            
            elif action == "TOGGLEKODISETTING":
                kodisetting = params.get("SETTING")
                toggleKodiSetting(kodisetting)
            
            elif action == "ENABLEVIEWS":
                enableViews()
                
            elif action == "SPLASHSCREEN":
                file = params.get("FILE","")
                duration = params.get("DURATION","")
                if duration:
                    show_splash(file,int(duration))
                else:
                    show_splash(file)
            
            elif action == "VIDEOSEARCH":
                from resources.lib.SearchDialog import SearchDialog
                searchDialog = SearchDialog("script-skin_helper_service-CustomSearch.xml", ADDON_PATH, "Default", "1080i")
                searchDialog.doModal()
                del searchDialog
            
            elif action == "COLORPICKER":
                from resources.lib.ColorPicker import ColorPicker
                colorPicker = ColorPicker("script-skin_helper_service-ColorPicker.xml", ADDON_PATH, "Default", "1080i")
                colorPicker.skinString = params.get("SKINSTRING","")
                colorPicker.winProperty = params.get("WINPROPERTY","")
                colorPicker.activePalette = params.get("PALETTE","")
                colorPicker.headerLabel = params.get("HEADER","")
                propname = params.get("SHORTCUTPROPERTY","")
                colorPicker.shortcutProperty = propname
                colorPicker.doModal()
                if propname:
                    wid = xbmcgui.getCurrentWindowDialogId()
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
                colorThemes = ColorThemes("DialogSelect.xml", ADDON_PATH)
                colorThemes.daynight = params.get("DAYNIGHT",None)
                colorThemes.doModal()
                del colorThemes
            
            elif action == "CONDITIONALBACKGROUNDS":
                from resources.lib.ConditionalBackgrounds import ConditionalBackgrounds
                conditionalBackgrounds = ConditionalBackgrounds("DialogSelect.xml", ADDON_PATH)
                conditionalBackgrounds.doModal()
                del conditionalBackgrounds
            
            elif action == "CREATECOLORTHEME":
                import resources.lib.ColorThemes as colorThemes
                colorThemes.createColorTheme()
            
            elif action == "RESTORECOLORTHEME":
                import resources.lib.ColorThemes as colorThemes
                colorThemes.restoreColorTheme()
            
            elif action == "OVERLAYTEXTURE":    
                selectOverlayTexture()
            
            elif action == "BUSYTEXTURE":    
                selectBusyTexture()

            elif action == "RESETCACHE":
                path = params.get("PATH")
                if path == "pvr":
                    path = WINDOW.getProperty("SkinHelper.pvrthumbspath").decode("utf-8")
                    WINDOW.setProperty("resetPvrArtCache","reset")
                elif path == "music":
                    path = "special://profile/addon_data/script.skin.helper.service/musicart/"
                    WINDOW.setProperty("resetMusicArtCache","reset")
                elif path == "wallbackgrounds":
                    path = "special://profile/addon_data/script.skin.helper.service/wallbackgrounds/"
                    WINDOW.setProperty("resetWallArtCache","reset")
                else: path = None
                
                if path:
                    success = True
                    ret = xbmcgui.Dialog().yesno(heading=ADDON.getLocalizedString(32089), line1=ADDON.getLocalizedString(32090)+path)
                    if ret:
                        success = recursiveDelete(path)
                        if success:
                            xbmcgui.Dialog().ok(heading=ADDON.getLocalizedString(32089), line1=ADDON.getLocalizedString(32091))
                        else:
                            xbmcgui.Dialog().ok(heading=ADDON.getLocalizedString(32089), line1=ADDON.getLocalizedString(32092))
                    
            
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
                backup.reset()
            
            elif action == "DIALOGOK":
                headerMsg = params.get("HEADER")
                bodyMsg = params.get("MESSAGE")
                xbmcgui.Dialog().ok(heading=headerMsg, line1=bodyMsg)
            


if (__name__ == "__main__"):
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    if not WINDOW.getProperty("SkinHelper.KodiExit"):
        Main()
    
logMsg('finished loading script entry')

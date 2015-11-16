import xbmcaddon,xbmc,xbmcvfs,xbmcgui
import os
from xml.dom.minidom import parse
import math
import json
from traceback import print_exc

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path').decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)

def fullMigration():
    #migrate function
    # to migrate all current user settings to the new skinhelper and skinshortcuts
    migrateLog = ""
    xbmc.sleep(500)
    while WINDOW.getProperty( "skinshortcuts-isrunning" ) == "True":
        xbmc.sleep(500)
    
    if not WINDOW.getProperty("titanmigration"):
        #user choose to perform the migration
        WINDOW.setProperty("titanmigration","running")
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            log = "TITAN SKIN --> Starting migration of Titan skin \n"

            #first make backup
            log += "TITAN SKIN --> Creating backup \n"
            xbmc.executebuiltin( "RunScript(script.skin.helper.service,action=backup,silent=special://temp/titan_pre-migration_backup.zip)" )
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            
            log += "TITAN SKIN --> migrate color settings... \n"
            migrateColorSettings()
            log += "TITAN SKIN --> migrate color themes... \n"
            migrateColorThemes()
            log += "TITAN SKIN --> migrate other skin settings... \n"
            migrateOtherSkinSettings()
            log += "TITAN SKIN --> migrate skin helper settings... \n"
            migrateSkinHelperSettings()
            log += "TITAN SKIN --> migrate skin shortcuts... \n"
            migrateSkinShortcuts()
        except:
            log += "TITAN SKIN --> Error while Creating backup \n"
            print_exc()
            #reset all settings to defaults
            xbmc.executebuiltin("Skin.ResetSettings")
            xbmc.executebuiltin("RunScript(script.skinshortcuts,type=resetall&warning=false)")
            xbmc.sleep(500)
            xbmc.executebuiltin("ReloadSkin")                
        finally:
            try:
                logfile = xbmc.translatePath("special://temp/titan_pre-migration_backup.log").decode("utf-8")
                with open(logfile, 'w') as f:
                    f.write(log)
                    xbmc.log(log)
            except: pass
            WINDOW.clearProperty("titanmigration")
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )


def getMigratedSkinSettings():
    settingsList = []
    settingsList.append(("ColorThemeTexture","BackgroundOverlayTexture"))
    settingsList.append(("CustomColorThemeTexture","CustomBackgroundOverlayTexture"))
    settingsList.append(("ColorTheme","BackgroundOverlayColor"))
    settingsList.append(("ColorTheme.name","BackgroundOverlayColor.name"))
    settingsList.append(("GadgetRows","HomeLayout"))
    
    return settingsList
    
def getMigratedSkinSetting(settingname):
    #check the settingname in the list of changed settings and return the new version
    settingsList = getMigratedSkinSettings()
    for setting in settingsList:
        if setting[0] == settingname:
            settingname = setting[1]
    return settingname

def migrateOtherSkinSettings():
    settingsList = getMigratedSkinSettings()
    for setting in settingsList:
        currentvalue = xbmc.getInfoLabel("$INFO[Skin.String(%s)]" %setting[0]).decode("utf-8")
        if currentvalue:
            xbmc.executebuiltin("Skin.SetString(%s,%s)" %(setting[1],currentvalue))
            xbmc.executebuiltin("Skin.Reset(%s)" %setting[0])
    
def migrateSkinHelperSettings():
    #migrate string settings
    settings = ["ShowInfoAtPlaybackStart","RandomFanartDelay","SpinnerTexture","SpinnerTexturePath","ForcedViews.movies","ForcedViews.tvshows","ForcedViews.seasons","ForcedViews.episodes","ForcedViews.sets","ForcedViews.setmovies"]
    for setting in settings:
        currentvalue = xbmc.getInfoLabel("$INFO[Skin.String(%s)]" %setting).decode("utf-8")
        xbmc.executebuiltin("Skin.SetString(SkinHelper.%s,%s)" %(setting,currentvalue))
        xbmc.executebuiltin("Skin.Reset(%s)" %setting)
    
    #migrate bool settings
    settings = ["ForcedViews.Enabled"]
    for setting in settings:
        currentvalue = xbmc.getCondVisibility("Skin.HasSetting(%s)" %setting)
        if currentvalue:
            xbmc.executebuiltin("Skin.SetBool(SkinHelper.%s)" %setting)
        xbmc.executebuiltin("Skin.Reset(%s)" %setting)
 
def getAllColors():
    #get all colors from the colors xml file and fill a list with tuples to sort later on
    allColors = []
    colors_file = xbmc.translatePath("special://home/addons/script.skin.helper.service/resources/colors/colors.xml").decode("utf-8")
    if xbmcvfs.exists( colors_file ):
        doc = parse( colors_file )
        listing = doc.documentElement.getElementsByTagName( 'color' )
        for count, color in enumerate(listing):
            name = color.attributes[ 'name' ].nodeValue.lower()
            colorstring = color.childNodes [ 0 ].nodeValue.lower()
            allColors.append((name,colorstring))
    
    #get skin colors too
    colors_file = xbmc.translatePath("special://skin/colors/defaults.xml").decode("utf-8")
    if xbmcvfs.exists( colors_file ):
        doc = parse( colors_file )
        listing = doc.documentElement.getElementsByTagName( 'color' )
        for count, color in enumerate(listing):
            name = color.attributes[ 'name' ].nodeValue.lower()
            colorstring = color.childNodes [ 0 ].nodeValue.lower()
            allColors.append((name,colorstring))
            
    return allColors
 
def migrateColorSettings():
    
    xbmc.log("TITAN SKIN --> Migrating Color settings.....")
    
    if KODI_VERSION >= 16:
        xbmc.executebuiltin("Reloadskin")
        xbmc.sleep(1500)
    
    #get all colors from the colors xml file and fill a list with tuples to sort later on
    allColors = getAllColors()
    
    #read the guisettings file to get all skin settings
    skinsettingsList = []
    if KODI_VERSION < 16:
        guisettings_path = 'special://profile/guisettings.xml'
    else:
        guisettings_path = 'special://profile/addon_data/%s/settings.xml' %xbmc.getSkinDir()
    if xbmcvfs.exists(guisettings_path):
        guisettings_path = xbmc.translatePath(guisettings_path).decode("utf-8")
        retries = 3
        for i in range(retries):
            try:
                doc = parse(guisettings_path)
                break
            except:
                xbmc.sleep(1000)
        
        skinsettings = doc.documentElement.getElementsByTagName('setting')
        
        for count, skinsetting in enumerate(skinsettings):
            
            if KODI_VERSION < 16:
                settingname = skinsetting.attributes['name'].nodeValue
            else:
                settingname = skinsetting.attributes['id'].nodeValue
            
            #only get settings for the current skin
            if ( KODI_VERSION < 16 and settingname.startswith(xbmc.getSkinDir()+".")) or KODI_VERSION >= 16:
                
                if skinsetting.childNodes:
                    settingvalue = skinsetting.childNodes[0].nodeValue
                else:
                    settingvalue = ""
                
                settingname = settingname.replace(xbmc.getSkinDir()+".","")
                if settingname.startswith("beta.") or settingname.startswith("helix."):
                    continue
                settingtype = skinsetting.attributes['type'].nodeValue
                
                
                if settingname.lower().endswith("color") or settingname.lower() == "colortheme":
                    colorname = "None"
                    colorvalue = "None"
                    matchfound = False
                    for color in allColors:
                        if settingvalue.lower() == color[0].lower() or settingvalue.lower() == color[1].lower():
                            colorvalue = color[1]
                            colorname = color[0]
                            matchfound = True
                            break
                    
                    if not settingvalue or settingvalue.lower() == "none" or settingvalue.upper()=="00FFFFFF":
                        colorname = "None"
                        colorvalue = "None"
                    elif matchfound == False:
                        colorvalue = settingvalue
                    
                    #check for old opacity setting...
                    if not colorvalue == "None":
                        opacity = xbmc.getInfoLabel("$INFO[Skin.String(%s)]" %settingname.replace("Color","Opacity")).decode("utf-8")
                        if opacity:
                            xbmc.sleep(1000)
                            try:
                                num = int(opacity) / 100.0 * 255
                                e = num - math.floor( num )
                                a = e < 0.5 and int( math.floor( num ) ) or int( math.ceil( num ) )
                                
                                colorstring = colorvalue.strip()
                                r, g, b = colorstring[2:4], colorstring[4:6], colorstring[6:]
                                r, g, b = [int(n, 16) for n in (r, g, b)]
                                color = (a, r, g, b)
                                colorvalue = '%02x%02x%02x%02x' % color
                                xbmc.executebuiltin("Skin.Reset(%s)" %settingname.replace("Color","Opacity"))
                            except Exception as e:
                                xbmc.log("Error has occurred while correcting " + settingname)
                                xbmc.log(str(e))
                                xbmc.executebuiltin("Skin.Reset(%s)" %settingname.replace("Color","Opacity"))
                    
                    if matchfound == False and not colorvalue == "None":
                        colorname = "Custom " + colorvalue
                    xbmc.executebuiltin("Skin.SetString(%s,%s)" %(settingname,colorvalue))
                    xbmc.executebuiltin("Skin.SetString(%s.name,%s)" %(settingname,colorname))
                    if colorvalue and not colorvalue == "None":
                        colorbase = "ff" + colorvalue[2:]
                        xbmc.executebuiltin("Skin.SetString(%s.base,%s)" %(settingname,colorbase))
                    else: 
                        xbmc.executebuiltin("Skin.Reset(%s.base)" %settingname)
                                           
def migrateColorThemes():
    #migrates any colorthemes setup by the user
    skin = xbmcaddon.Addon(id=xbmc.getSkinDir())
    userThemesDir = xbmc.translatePath(skin.getAddonInfo('profile')).decode("utf-8")
    userThemesPath = os.path.join(userThemesDir,"themes") + os.sep
    allColors = getAllColors()
    dirs, files = xbmcvfs.listdir(userThemesPath)
    for file in files:
        if file.endswith(".theme"):
            settingsList = []
            f = open(os.path.join(userThemesPath,file),"r")
            importstring = json.load(f)
            f.close()
            for count, skinsetting in enumerate(importstring):
                if skinsetting[0] == "DESCRIPTION" or skinsetting[0] == "THEMENAME" or skinsetting[0] == "SKINFONT" or skinsetting[0] == "SKINCOLORS" or skinsetting[0] == "SKINTHEME":
                    settingsList.append(skinsetting)
                elif not "opacity" in skinsetting[1].lower() and not ".helix" in skinsetting[1].lower():
                    settingtype = skinsetting[0]
                    settingname = skinsetting[1]
                    settingvalue = skinsetting[2]
                    colorname = "None"
                    colorvalue = "None"
                    opacity = None
                    matchfound = False
                    
                    if settingname.lower().endswith("color") or settingname.endswith("colortheme"):
                        for color in allColors:
                            if settingvalue.lower() == color[0].lower() or settingvalue.lower() == color[1].lower():
                                colorvalue = color[1]
                                colorname = color[0]
                                matchfound = True
                                break
                        
                        if not settingvalue or settingvalue.lower() == "none" or settingvalue.upper()=="00FFFFFF":
                            colorname = "None"
                            colorvalue = "None"
                        elif matchfound == False:
                            colorvalue = settingvalue
                            print "no match found for color %s in theme %s - setting %s" %(settingvalue, file, settingname)
                        
                        #check for old opacity setting...
                        if not colorvalue == "None":
                            opacitysetting = settingname.lower().replace("color","opacity")
                            for count2, skinsetting2 in enumerate(importstring):
                                if skinsetting2[1].lower() == opacitysetting:
                                    opacity = skinsetting2[2]
                                    break

                            if opacity:
                                try:
                                    num = int(opacity) / 100.0 * 255
                                    e = num - math.floor( num )
                                    a = e < 0.5 and int( math.floor( num ) ) or int( math.ceil( num ) )
                                    
                                    colorstring = colorvalue.strip()
                                    r, g, b = colorstring[2:4], colorstring[4:6], colorstring[6:]
                                    r, g, b = [int(n, 16) for n in (r, g, b)]
                                    color = (a, r, g, b)
                                    colorvalue = '%02x%02x%02x%02x' % color
                                except Exception as e:
                                    xbmc.log("Error has occurred while correcting " + settingname)
                                    xbmc.log(str(e))
                        if matchfound == False and not colorvalue == "None":
                            colorname = "Custom " + colorvalue
                    settingname = settingname.replace("TITANSKIN.","")
                    settingname = getMigratedSkinSetting(settingname)
                    if settingname.lower().endswith("color") or settingname.lower() == "colortheme":
                        settingsList.append( (settingtype, settingname, colorvalue) )
                        settingsList.append( (settingtype, settingname+".name", colorname) )
                    else:
                        settingsList.append( (settingtype, settingname, settingvalue) )
                        
            #save the migrated theme
            text_file = xbmcvfs.File(os.path.join(userThemesPath,file), "w")
            json.dump(settingsList, text_file)
            text_file.close()
                    
def migrateSkinShortcuts():
    propertiesList = []
    xbmc.log("TITAN SKIN --> Migrating Widget and background settings.....")
 
    #read existing properties
    propertiesfile = xbmc.translatePath("special://home/userdata/addon_data/script.skinshortcuts/%s.properties" %xbmc.getSkinDir()).decode("utf-8")
    if xbmcvfs.exists( propertiesfile ):
        f = open(propertiesfile, "r")
        for line in f:
            line = line.replace("[[","[").replace("]]","]").replace(",\n","").replace("\n","")
            if line.startswith("['") or line.startswith(" ['"):
                propertiesList.append(line)
        f.close()
        
    #Migrate skin shortcuts - convert widget settings
    skinshortcutspath = xbmc.translatePath("special://home/userdata/addon_data/script.skinshortcuts/mainmenu.DATA.xml").decode("utf-8")
    if xbmcvfs.exists( skinshortcutspath ):       
        doc = parse( skinshortcutspath )
        listing = doc.documentElement.getElementsByTagName( 'shortcut' )
        for shortcut in listing:
            
            #check visbility condition - to cleanup non-exististing shortcuts
            visible = shortcut.getElementsByTagName( 'visible' )
            if visible:
                visible = visible[0].firstChild.data
                if not xbmc.getCondVisibility(visible):
                    doc.documentElement.removeChild(shortcut)
                    continue
        
            defaultID = shortcut.getElementsByTagName( 'defaultID' )
            if defaultID:
                defaultID = defaultID[0].firstChild
                if defaultID:
                    defaultID = defaultID.data
                    label = shortcut.getElementsByTagName( 'label' )[0].firstChild.data
                    widget = xbmc.getInfoLabel("$INFO[Skin.String(widget-%s)]" %defaultID)
                    if not widget:
                        widget = xbmc.getInfoLabel("$INFO[Skin.String(widget-%s)]" %label)
                        if "&" in widget and not "&amp;" in widget:
                            widget = widget.replace("&","&amp;")
                    xbmc.executebuiltin("Skin.Reset(widget-%s)" %defaultID)
                    widgetPropExists = False
                    backgroundPropExists = False
                    
                    for line in propertiesList:
                        if "widget" in line and "'" + defaultID + "'" in line:
                            widgetPropExists = True
                        if "background" in line and "'" + defaultID + "'" in line:
                            backgroundPropExists = True
                    
                    if widget and not widgetPropExists:
                        if widget == "weather":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'weather']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[12600]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'$INCLUDE[WeatherWidget]']"%defaultID)
                        elif widget == "movies":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'recommendedmovies']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$ADDON[script.skin.helper.service 32003]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'movies']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'plugin://script.skin.helper.service/?action=RECOMMENDEDMOVIES&reload=$INFO[Window(Home).Property(widgetreload)]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widget.1', u'recentmovies']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName.1', u'31127']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType.1', u'movies']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget.1', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath.1', u'special://skin/extras/widgetplaylists/recentmovies.xsp']"%defaultID)
                        elif widget == "tvshows":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'nextepisodes']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$ADDON[script.skin.helper.service 32002]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'episodes']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'plugin://script.skin.helper.service/?action=nextepisodes&reload=$INFO[Window(Home).Property(widgetreload)]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widget.1', u'recentepisodes']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName.1', u'31127']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType.1', u'episodes']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget.1', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath.1', u'special://skin/extras/widgetplaylists/recentepisodes.xsp']"%defaultID)
                        elif widget == "youtube":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'popularyoutube']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[31563]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'plugin://plugin.video.youtube/special/popular_right_now/']"%defaultID)
                        elif widget == "systeminfo":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'systeminfo']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[130]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'$INCLUDE[SystemInfoWidget]']"%defaultID)
                        elif widget == "submenuaswidget":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'submenuaswidget']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[31196]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'static']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'$INCLUDE[skinshortcuts-submenu]']"%defaultID)
                        elif widget == "music":
                            propertiesList.append("['mainmenu', '%s', 'widget', u'recentalbums']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[359]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'songs']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'music']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'plugin://script.skin.helper.service/?action=recentalbums&limit=25&reload=$INFO[Window(Home).Property(widgetreloadmusic)]']"%defaultID)
                        elif widget == "custom" and "window-home-property" in defaultID:
                            propertiesList.append("['mainmenu', '%s', 'widget', u'custom']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'%s']"%(defaultID,label.replace(".title",".recent.title")))
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'%s']"%(defaultID,label.replace(".title",".recent.content")))
                            propertiesList.append("['mainmenu', '%s', 'widgetName.1', u'%s']"%(defaultID,label.replace(".title",".inprogress.title")))
                            propertiesList.append("['mainmenu', '%s', 'widgetType.1', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget.1', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath.1', u'%s']"%(defaultID,label.replace(".title",".inprogress.content")))
                        elif widget == "custom" and "musicvideo" in defaultID:
                            propertiesList.append("['mainmenu', '%s', 'widget', u'musicvideos']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[20390]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'musicvideos']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'videodb://recentlyaddedmusicvideos/']"%defaultID)
                        else:
                            propertiesList.append("['mainmenu', '%s', 'widget', u'custom']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetName', u'$LOCALIZE[636]']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetType', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetTarget', u'video']"%defaultID)
                            propertiesList.append("['mainmenu', '%s', 'widgetPath', u'%s']"%(defaultID,widget))

                    if not backgroundPropExists:
                        if defaultID == "movies":
                            propertiesList.append("['mainmenu', 'movies', 'background', u'$INFO[Window(Home).Property(SkinHelper.AllMoviesBackground)]']")
                            propertiesList.append("['mainmenu', 'movies', 'backgroundName', u'$ADDON[script.skin.helper.service 32039]']")
                        elif defaultID == "tvshows":
                            propertiesList.append("['mainmenu', 'tvshows', 'background', u'$INFO[Window(Home).Property(SkinHelper.AllTvShowsBackground)]']")
                            propertiesList.append("['mainmenu', 'tvshows', 'backgroundName', u'$ADDON[script.skin.helper.service 32043]']")    
                        elif defaultID == "livetv":
                            propertiesList.append("['mainmenu', 'livetv', 'background', u'special://skin/extras/backgrounds/hover_my tv.jpg']")
                            propertiesList.append("['mainmenu', 'livetv', 'backgroundName', u'$LOCALIZE[10040]']")
                        if defaultID == "music":
                            propertiesList.append("['mainmenu', 'music', 'background', u'$INFO[Window(Home).Property(SkinHelper.AllMusicBackground)]']")
                            propertiesList.append("['mainmenu', 'music', 'backgroundName', u'$ADDON[script.skin.helper.service 32048]']")
                        if defaultID == "musicvideos":
                            propertiesList.append("['mainmenu', 'musicvideos', 'background', u'$INFO[Window(Home).Property(SkinHelper.AllMusicVideosBackground)]']")
                            propertiesList.append("['mainmenu', 'musicvideos', 'backgroundName', u'$ADDON[script.skin.helper.service 32047]']")
                        if defaultID == "weather":
                            propertiesList.append("['mainmenu', 'weather', 'background', u'$VAR[WeatherFanArtPath]$INFO[Window(Weather).Property(Current.FanartCode)]']")
                            propertiesList.append("['mainmenu', 'weather', 'backgroundName', u'$LOCALIZE[8]']")
                        if defaultID == "plugin.video.youtube":
                            propertiesList.append("['mainmenu', 'plugin.video.youtube', 'background', u'special://skin/extras/backgrounds/hover_extensions.jpg']")
                            propertiesList.append("['mainmenu', 'plugin.video.youtube', 'backgroundName', u'$LOCALIZE[10040]']")
                        if defaultID == "pictures":
                            propertiesList.append("['mainmenu', 'pictures', 'background', u'$INFO[Window(Home).Property(SkinHelper.PicturesBackground)]']")
                            propertiesList.append("['mainmenu', 'pictures', 'backgroundName', u'$ADDON[script.skin.helper.service 32046]']")
                        if defaultID == "10040":
                            propertiesList.append("['mainmenu', '10040', 'background', u'special://skin/extras/backgrounds/programs.jpg']")
                            propertiesList.append("['mainmenu', '10040', 'backgroundName', u'$LOCALIZE[10040]']")
                        if defaultID == "videos" or defaultID=="10006" or defaultID=="Videos":
                            propertiesList.append("['mainmenu', 'videos', 'background', u'$INFO[Window(Home).Property(SkinHelper.GlobalFanartBackground)]']")
                            propertiesList.append("['mainmenu', 'videos', 'backgroundName', u'$ADDON[script.skin.helper.service 32038]']")
                        if defaultID == "settings":
                            propertiesList.append("['mainmenu', 'settings', 'background', u'special://skin/extras/backgrounds/systeminfo.jpg']")
                            propertiesList.append("['mainmenu', 'settings', 'backgroundName', u'$LOCALIZE[10040]']")
                    
                    #migrate thumb to icon
                    try:
                        icon = shortcut.getElementsByTagName( 'icon' )[0].firstChild
                        thumb = shortcut.getElementsByTagName( 'thumb' )[0].firstChild
                        if icon:
                            if icon: icon = icon.data
                            if thumb: thumb = thumb.data
                            if icon and not thumb:
                                textnode = doc.createTextNode(icon)
                                shortcut.getElementsByTagName( 'thumb' ).item(0).appendChild(textnode)
                                defaultIcon = "special://skin/extras/hometiles/addons.png"
                                if defaultID == "movies": defaultIcon = "special://skin/extras/hometiles/movies.png"
                                if defaultID == "tvshows": defaultIcon = "special://skin/extras/hometiles/tvseries.png"
                                if defaultID == "music": defaultIcon = "special://skin/extras/hometiles/music.png"
                                if defaultID == "musicvideos": defaultIcon = "special://skin/extras/backgrounds/hover_my music.jpg"
                                if defaultID == "pictures": defaultIcon = "special://skin/extras/hometiles/pictures.png"
                                if defaultID == "weather": defaultIcon = "special://skin/extras/hometiles/weather.png"
                                if defaultID == "videos": defaultIcon = "special://skin/extras/hometiles/videos.png"
                                if defaultID == "settings": defaultIcon = "special://skin/extras/hometiles/settings.png"
                                shortcut.getElementsByTagName( 'icon' ).item(0).firstChild.data = defaultIcon
                    except: pass
                    
        xbmcvfs.delete(skinshortcutspath)
        with open(skinshortcutspath, 'w') as f:
            f.write(doc.toxml(encoding='utf-8'))


    #write the properties list
    if propertiesList:
        TotalCount = len(propertiesList)
        count = 1
        f = open(propertiesfile, "w")
        for line in propertiesList:
            if count == 1:
                f.write("[" + line + ",\n")
            elif count == TotalCount:
                f.write(line+"]")
            else:
                f.write(line + ",\n")
            count += 1
        f.close()
        
    
    # migrate skin shortcuts - replace VARs
    skinshortcutspath = xbmc.translatePath("special://home/userdata/addon_data/script.skinshortcuts/").decode("utf-8")
    if xbmcvfs.exists( skinshortcutspath ):
        dirs, files = xbmcvfs.listdir(skinshortcutspath)
        for file in files:
            f = open(skinshortcutspath+file, "r")
            contents = f.read() 
            f.close()
            contents = contents.replace("$VAR[MusicButtonThumb]","$INFO[Window(Home).Property(SkinHelper.AllMusicBackground)]")
            contents = contents.replace("$VAR[MoviesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.AllMoviesBackground)]")
            contents = contents.replace("$VAR[MoviesGenresButtonThumb]","$INFO[Window(Home).Property(SkinHelper.AllMoviesBackground)]")
            contents = contents.replace("$VAR[TvseriesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.AllTvShowsBackground)]")
            contents = contents.replace("$VAR[MusicVideosButtonThumb]","$INFO[Window(Home).Property(SkinHelper.AllMusicVideosBackground)]")
            contents = contents.replace("$VAR[WeatherButtonThumb]","special://skin/extras/weather/$INFO[Window(Weather).Property(Current.FanartCode)]/weather.jpg")
            contents = contents.replace("$VAR[PicturesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.PicturesBackground)]")
            contents = contents.replace("$VAR[InProgressMoviesButtonOnClick]","ActivateWindow(10025,special://skin/extras/widgetplaylists/inprogressmovies.xsp)")
            contents = contents.replace("$VAR[UnwatchedMoviesButtonOnClick]","ActivateWindow(10025,special://skin/extras/widgetplaylists/unwatchedmovies.xsp)")
            contents = contents.replace("$VAR[InProgressMoviesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.InProgressMoviesBackground)]")
            contents = contents.replace("$VAR[UnwatchedMoviesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.UnwatchedMoviesBackground)]")
            contents = contents.replace("$VAR[RecentTVseriesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.RecentEpisodesBackground)]")
            contents = contents.replace("$VAR[InprogressTVseriesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.InProgressShowsBackground)]")
            contents = contents.replace("$VAR[RecentMoviesButtonThumb]","$INFO[Window(Home).Property(SkinHelper.RecentMoviesBackground)]")
            contents = contents.replace("$VAR[CustomCollectionClick]","SetFocus(4444)")
            contents = contents.replace("plugin://script.titanskin.helpers/?","plugin://script.skin.helper.service/?action=")
            contents = contents.replace("RunScript(script.titanskin.helpers,","RunScript(script.skin.helper.service,action=")
            contents = contents.replace("$VAR[MoviesButtonOnClick]","ActivateWindow(10025,videodb://movies/titles/,return)")
            contents = contents.replace("$VAR[MoviesTitlesButtonOnClick]","ActivateWindow(10025,videodb://movies/titles/,return)")
            contents = contents.replace("$VAR[TVseriesButtonOnClick]","ActivateWindow(10025,videodb://tvshows/titles/,return)")
            contents = contents.replace("$VAR[TVseriesTitleButtonOnClick]","ActivateWindow(10025,videodb://tvshows/titles/,return)")
            contents = contents.replace("$VAR[NetflixButtonOnClick]","ActivateWindow(10025,plugin://plugin.video.netflixbmc,return)")
            contents = contents.replace("$VAR[MusicButtonOnClick]","ActivateWindow(Music,musicdb://,return)")
            contents = contents.replace("$VAR[VideosButtonOnClick]","ActivateWindow(Video,return)")
            contents = contents.replace("$VAR[SettingsButtonOnClick]","ActivateWindow(Settings)")
            contents = contents.replace("$VAR[MusicVideosButtonOnClick]","ActivateWindow(10025,videodb://musicvideos/titles/,return)")
            contents = contents.replace("$VAR[PicturesButtonOnClick]","ActivateWindow(pictures,return)")
            contents = contents.replace("$VAR[MB3ChannelsThumb]","DefaultShortcut.png")
            
            f = open(skinshortcutspath+file, "w")
            f.write(contents)
            f.close()

    #rebuild skinshortcuts
    count = 0
    skinshortcutspath = xbmc.translatePath("special://home/userdata/addon_data/script.skinshortcuts/%s.hash" %xbmc.getSkinDir()).decode("utf-8")
    while count != 20 and not xbmcvfs.exists( skinshortcutspath ):
        xbmc.sleep(500)
        count += 1
    #delete the hashfile
    xbmcvfs.delete( skinshortcutspath )
    xbmc.sleep(500)
    xbmc.executebuiltin("RunScript(script.skinshortcuts,type=buildxml&mainmenuID=300&group=mainmenu|powermenu)")
        
def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc" : "2.0" , "method" : "' + method + '" , "params" : ' + params + ' , "id":1 }')

    jsonobject = json.loads(json_response.decode('utf-8','replace'))
   
    if(jsonobject.has_key('result')):
        return jsonobject['result']
    else:
        xbmc.log("no result " + str(jsonobject),0)
        xbmc.log('{ "jsonrpc" : "2.0" , "method" : "' + method + '" , "params" : ' + params + ' , "id":1 }',0)
        return {}  
    
    
    
                        
    
		

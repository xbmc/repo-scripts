from Utils import *
import Dialogs as dialogs


def musicSearch():
    xbmc.executebuiltin( "ActivateWindow(MusicLibrary)" )
    xbmc.executebuiltin( "SendClick(8)" )

def addShortcutWorkAround():
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    xbmc.executebuiltin('SendClick(301)')
    
    count = 0
    #wait for the empy item is focused
    while (count != 60 and xbmc.getCondVisibility("Window.IsActive(script-skinshortcuts.xml)")):
        if not xbmc.getCondVisibility("StringCompare(Container(211).ListItem.Property(path), noop)"):
            xbmc.sleep(100)
            count += 1
        else:
            break
        
    if xbmc.getCondVisibility("StringCompare(Container(211).ListItem.Property(path), noop) + Window.IsActive(script-skinshortcuts.xml)"):
        xbmc.executebuiltin('SendClick(401)')
                    
def selectOverlayTexture():
    overlaysList = []
    overlaysList.append("Custom Overlay Image")
    dirs, files = xbmcvfs.listdir("special://skin/extras/bgoverlays/")
    for file in files:
        if file.endswith(".png"):
            label = file.replace(".png","")
            overlaysList.append(label)
    
    overlaysList.append("None")
    
    dialog = xbmcgui.Dialog()
    ret = dialog.select(ADDON.getLocalizedString(32015), overlaysList)
    if ret == 0:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 2 , ADDON.getLocalizedString(32016), 'files')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(BackgroundOverlayTexture,Custom)")
            xbmc.executebuiltin("Skin.SetString(CustomBackgroundOverlayTexture,%s)" % custom_texture)
    else:
        xbmc.executebuiltin("Skin.SetString(BackgroundOverlayTexture,%s)" % overlaysList[ret])
        xbmc.executebuiltin("Skin.Reset(CustomBackgroundOverlayTexture)")

def selectBusyTexture():
    spinnersList = []
    
    currentSpinnerTexture = xbmc.getInfoLabel("Skin.String(SkinHelper.SpinnerTexture)")
    
    listitem = xbmcgui.ListItem(label="None")
    listitem.setProperty("icon","None")
    spinnersList.append(listitem)
    
    listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32052))
    listitem.setProperty("icon","")
    spinnersList.append(listitem)
    
    listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32053))
    listitem.setProperty("icon","")
    spinnersList.append(listitem)
    
    path = "special://skin/extras/busy_spinners/"
    if xbmcvfs.exists(path):
        dirs, files = xbmcvfs.listdir(path)
        
        for dir in dirs:
            listitem = xbmcgui.ListItem(label=dir)
            listitem.setProperty("icon",path + dir)
            spinnersList.append(listitem)
        
        for file in files:
            if file.endswith(".gif"):
                label = file.replace(".gif","")
                listitem = xbmcgui.ListItem(label=label)
                listitem.setProperty("icon",path + file)
                spinnersList.append(listitem)

    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=spinnersList, windowtitle=ADDON.getLocalizedString(32051),multiselect=False )
    
    count = 0
    for li in spinnersList:
        if li.getLabel() == currentSpinnerTexture:
            w.autoFocusId = count
        count += 1
         
    w.doModal()
    selectedItem = w.result
    del w
    
    if selectedItem == -1:
        return
    
    if selectedItem == 1:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 2 , ADDON.getLocalizedString(32052), 'files', mask='.gif')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % custom_texture)
    elif selectedItem == 2:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 0 , ADDON.getLocalizedString(32053), 'files')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % custom_texture)
    else:
        xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
        xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % spinnersList[selectedItem].getProperty("icon"))
                
def enableViews():
    allViews = []   
    views_file = xbmc.translatePath( 'special://skin/extras/views.xml' ).decode("utf-8")
    if xbmcvfs.exists( views_file ):
        doc = parse( views_file )
        listing = doc.documentElement.getElementsByTagName( 'view' )
        for count, view in enumerate(listing):
            id = view.attributes[ 'value' ].nodeValue
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue))
            desc = label + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue
            listitem = xbmcgui.ListItem(label=label,label2=desc)
            listitem.setProperty("id",id)
            if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.View.Disabled.%s)" %id):
                listitem.select(selected=True)
            allViews.append(listitem)
    
    w = dialogs.DialogSelectSmall( "DialogSelect.xml", ADDON_PATH, listing=allViews, windowtitle=ADDON.getLocalizedString(32017),multiselect=True )
    w.doModal()
    
    selectedItems = w.result
    if selectedItems != -1:
        itemcount = len(allViews) -1
        while (itemcount != -1):
            viewid = allViews[itemcount].getProperty("id")
            if itemcount in selectedItems:
                #view is enabled
                xbmc.executebuiltin("Skin.Reset(SkinHelper.View.Disabled.%s)" %viewid)
            else:
                #view is disabled
                xbmc.executebuiltin("Skin.SetBool(SkinHelper.View.Disabled.%s)" %viewid)
            itemcount -= 1    
    del w        

def setForcedView(contenttype):
    currentView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %contenttype)
    if not currentView:
        currentView = "0"
    viewid, viewlabel = selectView(contenttype, currentView, True)
    
    if viewid != None:
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, viewid))
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s.label,%s)" %(contenttype, viewlabel))
    
def setView():
    #sets the selected viewmode for the container
    contenttype = getCurrentContentType()
    if not contenttype: contenttype = "files"
        
    currentView = xbmc.getInfoLabel("Container.Viewmode").decode("utf-8")
    viewid, viewlabel = selectView(contenttype, currentView)
    currentForcedView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %contenttype)
    
    if viewid != None:
        #also store forced view    
        if contenttype and currentForcedView and currentForcedView != "None" and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)"):
            xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, viewid))
            xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s.label,%s)" %(contenttype, viewlabel))
            WINDOW.setProperty("SkinHelper.ForcedView",viewid)
            if not xbmc.getCondVisibility("Control.HasFocus(%s)" %currentForcedView):
                xbmc.sleep(100)
                xbmc.executebuiltin("Container.SetViewMode(%s)" %viewid)
                xbmc.executebuiltin("SetFocus(%s)" %viewid)
        else:
            WINDOW.clearProperty("SkinHelper.ForcedView")
        
        #set view
        xbmc.executebuiltin("Container.SetViewMode(%s)" %viewid)
    
def searchYouTube(title,windowHeader="",autoplay="",windowed=""):
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    libPath = "plugin://plugin.video.youtube/kodion/search/query/?q=" + title
    media_array = None
    allResults = []
    autoplay = autoplay.lower() == "true"
    windowed = windowed.lower() == "true"
    path = ""
    media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art","plot"], "directory": "%s", "media": "files", "limits": {"end":25} }' %libPath)
    for media in media_array:
        if not media["filetype"] == "directory":
            label = media["label"]
            label2 = media["plot"]
            image = None
            if media.has_key('art'):
                if media['art'].has_key('thumb'):
                    image = (media['art']['thumb'])
            path = media["file"]
            listitem = xbmcgui.ListItem(label=label, label2=label2, iconImage=image)
            listitem.setProperty("path",path)
            listitem.setProperty("icon",image)
            allResults.append(listitem)
            if autoplay: break
            
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    if not autoplay:
        w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allResults, windowtitle=windowHeader,multiselect=False )
        w.doModal()
        selectedItem = w.result
        del w
        if selectedItem != -1:
            path = allResults[selectedItem].getProperty("path")
    
    #play video...
    if path and windowed:
        xbmc.executebuiltin('PlayMedia("%s",1)' %path)
        if "Trailer" in title:
            WINDOW.setProperty("TrailerPlaying","Playing")
    elif path:
        if xbmc.getCondVisibility("Window.IsActive(script-skin_helper_service-CustomInfo.xml) | Window.IsActive(movieinformation)"):
            xbmc.executebuiltin("Dialog.Close(movieinformation)")
            xbmc.executebuiltin("Dialog.Close(script-skin_helper_service-CustomInfo.xml)")
            xbmc.sleep(1000)
        xbmc.executebuiltin('PlayMedia("%s")' %path)
            
def selectView(contenttype="other", currentView=None, displayNone=False):
    currentViewSelectId = None
    id = None
    label = ""
    allViews = []
    if displayNone:
        listitem = xbmcgui.ListItem(label="None")
        listitem.setProperty("id","None")
        allViews.append(listitem)
        
    views_file = xbmc.translatePath( 'special://skin/extras/views.xml' ).decode("utf-8")
    if xbmcvfs.exists( views_file ):
        doc = parse( views_file )
        listing = doc.documentElement.getElementsByTagName( 'view' )
        itemcount = 0
        for count, view in enumerate(listing):
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue))
            id = view.attributes[ 'value' ].nodeValue
            desc = label + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue.lower().split(",")
            if label.lower() == currentView.lower() or id == currentView:
                currentViewSelectId = itemcount
                if displayNone == True:
                    currentViewSelectId += 1
            if ("all" in type or contenttype.lower() in type) and (not "!" + contenttype.lower() in type) and not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.View.Disabled.%s)" %id):
                image = "special://skin/extras/viewthumbs/%s.jpg" %id
                listitem = xbmcgui.ListItem(label=label, label2=desc, iconImage=image)
                listitem.setProperty("id",id)
                listitem.setProperty("icon",image)
                allViews.append(listitem)
                itemcount +=1
    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allViews, windowtitle=ADDON.getLocalizedString(32054),multiselect=False )
    w.autoFocusId = currentViewSelectId
    w.doModal()
    selectedItem = w.result
    del w
    if selectedItem != -1:
        id = allViews[selectedItem].getProperty("id")
        label = allViews[selectedItem].getLabel()
        return (id,label)
    else:
        return (None,None)

def waitForSkinShortcutsWindow():
    #wait untill skinshortcuts is active window (because of any animations that may have been applied)
    for i in range(40):
        if not (xbmc.getCondVisibility("Window.IsActive(DialogSelect.xml) | Window.IsActive(script-skin_helper_service-ColorPicker.xml) | Window.IsActive(DialogKeyboard.xml)")):
            break
        else: xbmc.sleep(100)
        
def setSkinShortCutsProperty(setting="",windowHeader="",propertyName=""):
    curValue = xbmc.getInfoLabel("$INFO[Container(211).ListItem.Property(%s)]" %propertyName).decode("utf-8")
    if not curValue: curValue = "None"
    if setting:
        (value, label) = setSkinSetting(setting, windowHeader, None, curValue)
    else:
        value = xbmcgui.Dialog().input(windowHeader, curValue, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
    if value:
        waitForSkinShortcutsWindow()
        xbmc.executebuiltin("SetProperty(customProperty,%s)" %propertyName.encode("utf-8"))
        xbmc.executebuiltin("SetProperty(customValue,%s)" %value.encode("utf-8"))
        xbmc.executebuiltin("SendClick(404)")
        if setting:
            xbmc.sleep(250)
            xbmc.executebuiltin("SetProperty(customProperty,%s.name)" %propertyName.encode("utf-8"))
            xbmc.executebuiltin("SetProperty(customValue,%s)" %label.encode("utf-8"))
            xbmc.executebuiltin("SendClick(404)")

def multiSelect(item,windowHeader=""):
    allOptions = []
    options = item.getElementsByTagName( 'option' )
    for option in options:
        id = option.attributes[ 'id' ].nodeValue
        label = xbmc.getInfoLabel(option.attributes[ 'label' ].nodeValue).decode("utf-8")
        default = option.attributes[ 'default' ].nodeValue
        condition = option.attributes[ 'condition' ].nodeValue
        if condition and not xbmc.getCondVisibility(condition): continue
        listitem = xbmcgui.ListItem(label=label)
        listitem.setProperty("id",id)
        if xbmc.getCondVisibility("Skin.HasSetting(%s)" %id) or (not xbmc.getInfoLabel("Skin.String(defaultset_%s)" %id) and xbmc.getCondVisibility( default )):
            listitem.select(selected=True)
        allOptions.append(listitem)
    #show select dialog
    w = dialogs.DialogSelectSmall( "DialogSelect.xml", ADDON_PATH, listing=allOptions, windowtitle=windowHeader,multiselect=True )
    w.doModal()
    
    selectedItems = w.result
    if selectedItems != -1:
        itemcount = len(allOptions) -1
        while (itemcount != -1):
            skinsetting = allOptions[itemcount].getProperty("id")
            if itemcount in selectedItems:
                #option is enabled
                xbmc.executebuiltin("Skin.SetBool(%s)" %skinsetting)
            else:
                #option is disabled
                xbmc.executebuiltin("Skin.Reset(%s)" %skinsetting)
            #always set additional prop to define the defaults
            xbmc.executebuiltin("Skin.SetString(defaultset_%s,defaultset)" %skinsetting)
            itemcount -= 1    
    del w                        

def writeSkinConstants(listing):
    #writes the list of all skin constants
    addonpath = xbmc.translatePath( os.path.join( "special://skin/", 'addon.xml').encode("utf-8") ).decode("utf-8")
    addon = xmltree.parse( addonpath )
    extensionpoints = addon.findall( "extension" )
    paths = []
    for extensionpoint in extensionpoints:
        if extensionpoint.attrib.get( "point" ) == "xbmc.gui.skin":
            resolutions = extensionpoint.findall( "res" )
            for resolution in resolutions:
                includes_file = xbmc.translatePath( os.path.join("special://skin/" , try_decode( resolution.attrib.get( "folder" ) ), "script-skin_helper_service-includes.xml").encode("utf-8") ).decode('utf-8')
                tree = xmltree.ElementTree( xmltree.Element( "includes" ) )
                root = tree.getroot()
                for key, value in listing.iteritems():
                    if value:
                        child = xmltree.SubElement( root, "constant" )
                        child.text = try_decode(value)
                        child.attrib[ "name" ] = key
                indentXML( tree.getroot() )
                xmlstring = xmltree.tostring(tree.getroot(), encoding="utf-8")
                f = xbmcvfs.File(includes_file, 'w')
                f.write(xmlstring)
                f.close()
    xbmc.executebuiltin("ReloadSkin()")
    
def getSkinConstants():
    #gets a list of all skin constants
    allConstants = {}
    addonpath = xbmc.translatePath( os.path.join( "special://skin/", 'addon.xml').encode("utf-8") ).decode("utf-8")
    addon = xmltree.parse( addonpath )
    extensionpoints = addon.findall( "extension" )
    paths = []
    for extensionpoint in extensionpoints:
        if extensionpoint.attrib.get( "point" ) == "xbmc.gui.skin":
            resolutions = extensionpoint.findall( "res" )
            for resolution in resolutions:
                includes_file = xbmc.translatePath( os.path.join( "special://skin/" , try_decode( resolution.attrib.get( "folder" ) ), "script-skin_helper_service-includes.xml").encode("utf-8") ).decode('utf-8')
                if xbmcvfs.exists( includes_file ):
                    doc = parse( includes_file )
                    listing = doc.documentElement.getElementsByTagName( 'constant' )
                    for count, item in enumerate(listing):
                        name = item.attributes[ 'name' ].nodeValue
                        value = item.firstChild.nodeValue
                        allConstants[name] = value
    return allConstants

def updateSkinConstants(newValues):
    updateNeeded = False
    allValues = getSkinConstants()
    for key, value in newValues.iteritems():
        if allValues.has_key(key):
            if allValues.get(key) != value:
                updateNeeded = True
                allValues[key] = value
        else:
            updateNeeded = True
            allValues[key] = value
    if updateNeeded:
        writeSkinConstants(allValues)

def setSkinConstant(setting="", windowHeader=""):
    allCurrentValues = getSkinConstants()
    value, label = setSkinSetting(setting=setting, windowHeader=windowHeader, sublevel="", valueOnly=allCurrentValues.get(setting,"emptyconstant"))
    result = { setting:value }
    updateSkinConstants(result)
        
def setSkinSetting(setting="", windowHeader="", sublevel="", valueOnly=""):
    curValue = xbmc.getInfoLabel("Skin.String(%s)" %setting).decode("utf-8")
    if valueOnly: curValue = valueOnly
    curValueLabel = xbmc.getInfoLabel("Skin.String(%s.label)" %setting).decode("utf-8")
    useRichLayout = False
    selectId = 0
    itemcount = 0
    
    allValues = []        
    settings_file = xbmc.translatePath( 'special://skin/extras/skinsettings.xml' ).decode("utf-8")
    if xbmcvfs.exists( settings_file ):
        doc = parse( settings_file )
        listing = doc.documentElement.getElementsByTagName( 'setting' )
        if sublevel:
            listitem = xbmcgui.ListItem(label="..", iconImage="DefaultFolderBack.png")
            listitem.setProperty("icon","DefaultFolderBack.png")
            listitem.setProperty("value","||BACK||")
            allValues.append(listitem)
        for count, item in enumerate(listing):
            id = item.attributes[ 'id' ].nodeValue
            if id.startswith("$"): id = xbmc.getInfoLabel(id).decode("utf-8")
            label = xbmc.getInfoLabel(item.attributes[ 'label' ].nodeValue).decode("utf-8")
            if (not sublevel and id.lower() == setting.lower()) or (sublevel and sublevel.lower() == id.lower()):
                value = item.attributes[ 'value' ].nodeValue
                if value == "||MULTISELECT||": return multiSelect(item,windowHeader)
                condition = item.attributes[ 'condition' ].nodeValue
                icon = item.attributes[ 'icon' ].nodeValue
                description = item.attributes[ 'description' ].nodeValue
                description = xbmc.getInfoLabel(description.encode("utf-8"))
                if condition and not xbmc.getCondVisibility(condition): continue
                if icon: useRichLayout = True
                if icon and icon.startswith("$"): icon = xbmc.getInfoLabel(icon)
                if curValue and (curValue.lower() == value.lower() or label.lower() == curValueLabel.lower()): selectId = itemcount
                listitem = xbmcgui.ListItem(label=label, iconImage=icon)
                listitem.setProperty("value",value)
                listitem.setProperty("icon",icon)
                listitem.setProperty("description",description)
                listitem.setLabel2(description)
                #additional onselect actions
                additionalactions = []
                for action in item.getElementsByTagName( 'onselect' ):
                    condition = action.attributes[ 'condition' ].nodeValue
                    if condition and not xbmc.getCondVisibility(condition): continue
                    command = action.firstChild.nodeValue
                    if "$" in command: command = xbmc.getInfoLabel(command)
                    additionalactions.append(command)
                listitem.setProperty("additionalactions"," || ".join(additionalactions))
                allValues.append(listitem)
                itemcount +=1
        if not allValues:
            selectedItem = -1
        elif len(allValues) > 1:
            #only use select dialog if we have muliple values
            if useRichLayout:
                w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allValues, windowtitle=windowHeader,multiselect=False )
            else:
                w = dialogs.DialogSelectSmall( "DialogSelect.xml", ADDON_PATH, listing=allValues, windowtitle=windowHeader,multiselect=False )
            if selectId > 0 and sublevel: selectId += 1
            w.autoFocusId = selectId
            w.doModal()
            selectedItem = w.result
            del w
        else:
            selectedItem = 0
        #process the results
        if selectedItem != -1:
            value = try_decode( allValues[selectedItem].getProperty("value") )
            label = try_decode( allValues[selectedItem].getLabel() )
            description = allValues[selectedItem].getProperty("description")
            if value.startswith("||SUBLEVEL||"):
                sublevel = value.replace("||SUBLEVEL||","")
                setSkinSetting(setting, windowHeader, sublevel)
            elif value == "||BACK||":
                setSkinSetting(setting, windowHeader)
            else:
                if value == "||BROWSEIMAGE||":
                    if xbmcgui.Dialog().yesno( label, ADDON.getLocalizedString(32064), yeslabel=ADDON.getLocalizedString(32065), nolabel=ADDON.getLocalizedString(32066) ):
                        value = xbmcgui.Dialog().browse( 2 , label, 'files').decode("utf-8")
                    else: value = xbmcgui.Dialog().browse( 0 , ADDON.getLocalizedString(32067), 'files')
                if value == "||BROWSESINGLEIMAGE||":
                    value = xbmcgui.Dialog().browse( 2 , label, 'files').decode("utf-8")
                if value == "||PROMPTNUMERIC||":
                    value = xbmcgui.Dialog().input( label,curValue, 1).decode("utf-8")
                if value == "||PROMPTSTRING||":
                    value = xbmcgui.Dialog().input( label,curValue, 0).decode("utf-8")
                if value == "||PROMPTSTRINGASNUMERIC||":
                    validInput = False
                    while not validInput:
                        try:
                            value = xbmcgui.Dialog().input( label,curValue, 0).decode("utf-8")
                            valueint = int(value)
                            validInput = True
                        except:
                            value = xbmcgui.Dialog().notification( "Invalid input", "Please enter a number...")
                            
                #write skin strings
                if not valueOnly and value != "||SKIPSTRING||":
                    xbmc.executebuiltin("Skin.SetString(%s,%s)" %(setting.encode("utf-8"),value.encode("utf-8")))
                    xbmc.executebuiltin("Skin.SetString(%s.label,%s)" %(setting.encode("utf-8"),label.encode("utf-8")))
                #process additional actions
                additionalactions = allValues[selectedItem].getProperty("additionalactions").split(" || ")
                for action in additionalactions:
                    xbmc.executebuiltin(action)
                return (value,label)
        else: return (None,None)

def correctSkinSettings():
    #correct any special skin settings
    skinconstants = {}
    settings_file = xbmc.translatePath( 'special://skin/extras/skinsettings.xml' ).decode("utf-8")
    if xbmcvfs.exists( settings_file ):
        doc = parse( settings_file )
        listing = doc.documentElement.getElementsByTagName( 'setting' )
        for count, item in enumerate(listing):
            id = item.attributes[ 'id' ].nodeValue
            value = item.attributes[ 'value' ].nodeValue
            curvalue = xbmc.getInfoLabel("Skin.String(%s)" %id.encode("utf-8")).decode("utf-8")
            label = xbmc.getInfoLabel(item.attributes[ 'label' ].nodeValue).decode("utf-8")
            additionalactions = item.getElementsByTagName( 'onselect' )
            try: default = item.attributes[ 'default' ].nodeValue
            except: default = ""
            try: constantdefault = item.attributes[ 'constantdefault' ].nodeValue
            except: constantdefault = ""
            
            #skip submenu level itself, this happens when a setting id also exists as a submenu value for an item
            skip = False
            for count3, item3 in enumerate(listing):
                if item3.attributes[ 'value' ].nodeValue == "||SUBLEVEL||" + id:
                    skip = True
            if skip: continue
            
            #enumerate sublevel if needed
            if value.startswith("||SUBLEVEL||"):
                sublevel = value.replace("||SUBLEVEL||","")
                for count2, item2 in enumerate(listing):
                    if item2.attributes[ 'id' ].nodeValue == sublevel:
                        try: subdefault = item2.attributes[ 'default' ].nodeValue
                        except: subdefault = ""
                        try: subconstantdefault = item2.attributes[ 'constantdefault' ].nodeValue
                        except: subconstantdefault = ""
                        #match in sublevel or default found in sublevel values
                        if (item2.attributes[ 'value' ].nodeValue.lower() == curvalue.lower()) or (not curvalue and xbmc.getCondVisibility( subdefault )):
                            label = xbmc.getInfoLabel(item2.attributes[ 'label' ].nodeValue).decode("utf-8")
                            value = item2.attributes[ 'value' ].nodeValue
                            default = subdefault
                            additionalactions = item2.getElementsByTagName( 'onselect' )
                        if (item2.attributes[ 'value' ].nodeValue.lower() == curvalue.lower()) or xbmc.getCondVisibility( subconstantdefault ):
                            label = xbmc.getInfoLabel(item2.attributes[ 'label' ].nodeValue).decode("utf-8")
                            value = item2.attributes[ 'value' ].nodeValue
                            constantdefault = subconstantdefault
                            additionalactions = item2.getElementsByTagName( 'onselect' )
            #process any multiselects
            if value.startswith("||MULTISELECT||"):
                options = item.getElementsByTagName( 'option' )
                for option in options:
                    skinsetting = option.attributes[ 'id' ].nodeValue
                    if not xbmc.getInfoLabel("Skin.String(defaultset_%s)" %skinsetting) and xbmc.getCondVisibility( option.attributes[ 'default' ].nodeValue ):
                        xbmc.executebuiltin("Skin.SetBool(%s)" %skinsetting)
                    #always set additional prop to define the defaults
                    xbmc.executebuiltin("Skin.SetString(defaultset_%s,defaultset)" %skinsetting)
                        
            #only correct the label
            if value and value.lower() == curvalue.lower():
                xbmc.executebuiltin("Skin.SetString(%s.label,%s)" %(id.encode("utf-8"),label.encode("utf-8")))
            #set the default value if current value is empty
            if not curvalue and xbmc.getCondVisibility( default ):
                xbmc.executebuiltin("Skin.SetString(%s.label,%s)" %(id.encode("utf-8"),label.encode("utf-8")))
                xbmc.executebuiltin("Skin.SetString(%s,%s)" %(id.encode("utf-8"),value.encode("utf-8")))
                #additional onselect actions
                for action in additionalactions:
                    condition = action.attributes[ 'condition' ].nodeValue
                    if condition and not xbmc.getCondVisibility(condition): continue
                    command = action.firstChild.nodeValue
                    if "$" in command: command = xbmc.getInfoLabel(command)
                    xbmc.executebuiltin(command)
            #set the default constant value if current value is empty
            if xbmc.getCondVisibility( constantdefault ):
                skinconstants[id] = value
                #additional onselect actions
                for action in additionalactions:
                    condition = action.attributes[ 'condition' ].nodeValue
                    if condition and not xbmc.getCondVisibility(condition): continue
                    command = action.firstChild.nodeValue
                    if "$" in command: command = xbmc.getInfoLabel(command)
                    xbmc.executebuiltin(command)
    if skinconstants:
        updateSkinConstants(skinconstants)
                            
def toggleKodiSetting(settingname):
    #toggle kodi setting
    curValue = xbmc.getCondVisibility("system.getbool(%s)"%settingname)
    if curValue == True:
        newValue = "false"
    else:
        newValue = "true"
    xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %(settingname,newValue))
     
def show_splash(file,duration=5):
    logMsg("show_splash --> " + file)
    if file.lower().endswith("jpg") or file.lower().endswith("gif") or file.lower().endswith("png") or file.lower().endswith("tiff"):
        #this is an image file
        WINDOW.setProperty("SkinHelper.SplashScreen",file)
        #for images we just wait for X seconds to close the splash again
        start_time = time.time()
        while(time.time() - start_time <= duration):
            xbmc.sleep(500)
    else:
        #for video or audio we have to wait for the player to finish...
        xbmc.Player().play(file,windowed=True)
        xbmc.sleep(500)
        while xbmc.getCondVisibility("Player.HasMedia"):
            xbmc.sleep(150)

    #replace startup window with home
    startupwindow = xbmc.getInfoLabel("$INFO[System.StartupWindow]")
    xbmc.executebuiltin("ReplaceWindow(%s)" %startupwindow)
    
    #startup playlist (if any)
    AutoStartPlayList = xbmc.getInfoLabel("$ESCINFO[Skin.String(AutoStartPlayList)]")
    if AutoStartPlayList: xbmc.executebuiltin("PlayMedia(%s)" %AutoStartPlayList)

def checkResourceAddon(setting, addontype):
    #check for existing resource addons of this type and set first one found...
    addonFound = False
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"type": "kodi.resource.images", "properties": ["name", "thumbnail", "path"]}, "id": 1}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = json.loads(json_query)
    if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('addons'):
        addons = json_response['result']['addons']
        for item in addons:
            if item['addonid'].startswith(addontype):
                xbmc.executebuiltin("Skin.SetString(%s.path,resource://%s/)" %(setting,item['addonid']))
                xbmc.executebuiltin("Skin.SetString(%s.name,%s)" %(setting,item['name']))
                if ".multi" in item['addonid'] or "animated" in item['addonid']:
                    xbmc.executebuiltin("Skin.SetBool(%s.multi)" %(setting))
                return True
    return False
    
def checkResourceAddons(addonslist):
    addonslist = addonslist.split("|")
    for item in addonslist:
        setting = item.split(";")[0]
        addontype = item.split(";")[1]
        addontypelabel = item.split(";")[2]
        skinsetting = xbmc.getInfoLabel("Skin.String(%s.path)" %setting).decode("utf-8")
        if not skinsetting or ( skinsetting and xbmc.getCondVisibility("!System.HasAddon(%s)" %skinsetting.replace("resource://","").replace("/","")) ):
            #skin setting is empty or filled with non existing addon...
            if not checkResourceAddon(setting, addontype):
                ret = xbmcgui.Dialog().yesno(heading="%s missing!"%addontypelabel, 
                line1="To get the most out of this skin, it is suggested to install a resource addon for %s. \n Please install the resource addon(s) to your preference in the next dialog. You can always change your preference later in the skin settings." %addontypelabel)
                xbmc.executebuiltin("Skin.Reset(%s.path)" %setting)
                if ret:                   
                    xbmc.executebuiltin("ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/)")
                    #wait untill the addon is installed...
                    count = 0
                    while checkResourceAddon(setting, addontype)==False and count !=120:
                        xbmc.sleep(1000)
                        if xbmc.abortRequested: return

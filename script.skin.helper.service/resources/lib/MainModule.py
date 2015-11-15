from xml.dom.minidom import parse
from Utils import *

      
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
    
    import Dialogs as dialogs
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
    import Dialogs as dialogs
    
    allViews = []   
    views_file = xbmc.translatePath( 'special://skin/extras/views.xml' ).decode("utf-8")
    if xbmcvfs.exists( views_file ):
        doc = parse( views_file )
        listing = doc.documentElement.getElementsByTagName( 'view' )
        for count, view in enumerate(listing):
            id = view.attributes[ 'value' ].nodeValue
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue)) + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue
            listitem = xbmcgui.ListItem(label=label)
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
    selectedItem = selectView(contenttype, currentView, True, True)
    
    if selectedItem != -1 and selectedItem != None:
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, selectedItem))
    
def setView():
    #sets the selected viewmode for the container
    import Dialogs as dialogs
    
    #get current content type
    contenttype = getCurrentContentType()
        
    currentView = xbmc.getInfoLabel("Container.Viewmode").decode("utf-8")
    selectedItem = selectView(contenttype, currentView)
    currentForcedView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %contenttype)
    
    #also store forced view    
    if contenttype and currentForcedView and currentForcedView != "None" and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)"):
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, selectedItem))
        WINDOW.setProperty("SkinHelper.ForcedView",selectedItem)
        if not xbmc.getCondVisibility("Control.HasFocus(%s)" %currentForcedView):
            xbmc.sleep(100)
            xbmc.executebuiltin("Container.SetViewMode(%s)" %selectedItem)
            xbmc.executebuiltin("SetFocus(%s)" %selectedItem)
    else:
        WINDOW.clearProperty("SkinHelper.ForcedView")
    
    #set view
    if selectedItem != -1 and selectedItem != None:
        xbmc.executebuiltin("Container.SetViewMode(%s)" %selectedItem)
    
def searchYouTube(title,windowHeader=""):
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    import Dialogs as dialogs
    libPath = "plugin://plugin.video.youtube/kodion/search/query/?q=" + title
    media_array = None
    allResults = []
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
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allResults, windowtitle=windowHeader,multiselect=False )
    w.doModal()
    selectedItem = w.result
    del w
    if selectedItem != -1:
        path = allResults[selectedItem].getProperty("path")
        xbmc.executebuiltin("PlayMedia(%s)" %path)
            
def selectView(contenttype="other", currentView=None, displayNone=False, displayViewId=False):
    import Dialogs as dialogs
    currentViewSelectId = None

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
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue)).encode("utf-8").decode("utf-8")
            id = view.attributes[ 'value' ].nodeValue
            if displayViewId:
                label = label + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue.lower()
            if label.lower() == currentView.lower() or id == currentView:
                currentViewSelectId = itemcount
                if displayNone == True:
                    currentViewSelectId += 1
            if (type == "all" or contenttype.lower() in type) and not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.View.Disabled.%s)" %id):
                image = "special://skin/extras/viewthumbs/%s.jpg" %id
                listitem = xbmcgui.ListItem(label=label, iconImage=image)
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
        return id

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
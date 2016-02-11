from Utils import *

skin = xbmcaddon.Addon(id=xbmc.getSkinDir())
userThemesDir = xbmc.translatePath(skin.getAddonInfo('profile')).decode("utf-8")

class ColorThemes(xbmcgui.WindowXMLDialog):

    themesList = None
    userThemesPath = None
    skinThemesPath = None
    daynight = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
        self.userThemesPath = os.path.join(userThemesDir,"themes") + os.sep
        self.skinThemesPath = xbmc.translatePath("special://skin/extras/skinthemes/").decode("utf-8")
    
    def setDayNightTheme(self,item):
        selectedTheme = item.getLabel()
        #set a day/night theme 
        if self.daynight:
            currenttimevalue = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.time)" %self.daynight).decode("utf-8")
            if not currenttimevalue:
                if self.daynight == "night": currenttimevalue = "20:00"
                else: currenttimevalue = "07:00"
            timevalue = xbmcgui.Dialog().input(ADDON.getLocalizedString(32069),currenttimevalue, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
            
            try:
                #check if the time is valid
                dt = datetime(*(time.strptime(timevalue, "%H:%M")[0:6]))
                xbmc.executebuiltin(try_encode("Skin.SetString(SkinHelper.ColorTheme.%s.theme,%s)" % (self.daynight,selectedTheme)))
                xbmc.executebuiltin(try_encode("Skin.SetString(SkinHelper.ColorTheme.%s.time,%s)" % (self.daynight,timevalue)))
                xbmc.executebuiltin(try_encode("Skin.SetString(SkinHelper.ColorTheme.%s,%s  (%s %s))" % (self.daynight,selectedTheme,ADDON.getLocalizedString(32071),timevalue)))
                xbmc.executebuiltin(try_encode("Skin.SetString(SkinHelper.ColorTheme.%s.file,%s)" % (self.daynight,item.getProperty("filename"))))
            except:
                print_exc()
                xbmcgui.Dialog().ok(xbmc.getLocalizedString(329), ADDON.getLocalizedString(32070))

        self.closeDialog()
    
    def backupColorTheme(self, themeName, themeFile):
        
        import zipfile
        backup_path = get_browse_dialog(dlg_type=3,heading=ADDON.getLocalizedString(32018)).decode("utf-8")
        themeName = themeName.replace(" " + xbmc.getLocalizedString(461),"")
        if backup_path:
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            backup_name = xbmc.getSkinDir().replace("skin.","") + "_COLORTHEME_" + themeName
            backup_path = os.path.join(backup_path,backup_name)
            backup_path_temp = xbmc.translatePath('special://temp/' + backup_name).decode("utf-8")
            zf = zipfile.ZipFile("%s.zip" % (backup_path_temp), "w", zipfile.ZIP_DEFLATED)
            abs_src = os.path.abspath(self.userThemesPath)
            for dirname, subdirs, files in os.walk(self.userThemesPath):
                for filename in files:
                    if themeName in filename:
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        zf.write(absname, arcname)
            zf.close()
            xbmcvfs.copy(backup_path_temp + ".zip", backup_path + ".zip")
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
           
    def removeColorTheme(self,file):
        file = file.split(os.sep)[-1]
        themeName = file.replace(".theme","")
        xbmcvfs.delete(os.path.join(self.userThemesPath,themeName + ".jpg"))
        xbmcvfs.delete(os.path.join(self.userThemesPath,themeName + ".theme"))
        self.refreshListing()
        
    def renameColorTheme(self,file,themeNameOld):

        dialog = xbmcgui.Dialog()
        themeNameNew = dialog.input(ADDON.getLocalizedString(32146), themeNameOld.decode('utf-8'), type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
        if not themeNameNew:
            return
            
        f = open(file,"r")
        data = f.read()
        f.close()
        
        f = open(file,"w")
        data = data.replace(themeNameOld.decode('utf-8'), themeNameNew)
        f.write(data)
        f.close()
        
        if xbmcvfs.exists(file.replace(".theme",".jpg")):
            xbmcvfs.rename(file.replace(".theme",".jpg"), os.path.join(self.userThemesPath,themeNameNew + ".jpg"))
        xbmcvfs.rename(file, os.path.join(self.userThemesPath,themeNameNew + ".theme"))
        self.refreshListing()
    
    def setIconForColorTheme(self,file):
        file = file.split(os.sep)[-1]
        themeName = file.replace(".theme","")
        
        dialog = xbmcgui.Dialog()
        custom_thumbnail = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
        
        if custom_thumbnail:
            xbmcvfs.delete(os.path.join(self.userThemesPath,themeName + ".jpg"))
            xbmcvfs.copy(custom_thumbnail, os.path.join(self.userThemesPath, themeName + ".jpg"))

        self.refreshListing()
    
    def refreshListing(self):
        
        #clear list first
        self.themesList.reset()
        
        activetheme = xbmc.getInfoLabel("$INFO[Skin.String(SkinHelper.LastColorTheme)]").decode("utf-8")
        
        #add import and create items on top of the list
        listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32079), iconImage="-")
        desc = ADDON.getLocalizedString(32080)
        listitem.setProperty("description",desc)
        listitem.setProperty("Addon.Summary",desc)
        listitem.setLabel2(desc)
        listitem.setProperty("type","add")
        self.themesList.addItem(listitem)
        
        listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32081), iconImage="-")
        desc = ADDON.getLocalizedString(32082)
        listitem.setProperty("description",desc)
        listitem.setProperty("Addon.Summary",desc)
        listitem.setLabel2(desc)
        listitem.setProperty("type","import")
        self.themesList.addItem(listitem)
        
        
        #get all skin defined themes
        dirs, files = xbmcvfs.listdir(self.skinThemesPath)
        for file in files:
            if file.endswith(".theme"):
                icon = self.skinThemesPath+file.replace(".theme",".jpg")
                f = open(self.skinThemesPath+file,"r")
                importstring = json.load(f)
                f.close()
                for count, skinsetting in enumerate(importstring):
                    if skinsetting[0] == ("DESCRIPTION"):
                        desc = skinsetting[1]
                    if skinsetting[0] == ("THEMENAME"):
                        label = skinsetting[1]
                if label == activetheme and not self.daynight:
                    listlabel = label + " " + xbmc.getLocalizedString(461)
                else:
                    listlabel = label
                listitem = xbmcgui.ListItem(label=listlabel, iconImage=icon)
                listitem.setProperty("filename",self.skinThemesPath+file)
                listitem.setProperty("description",desc)
                listitem.setProperty("themename",label)
                listitem.setProperty("Addon.Summary",desc)
                listitem.setLabel2(desc)
                listitem.setProperty("type","skin")
                self.themesList.addItem(listitem)
        
        #get all user defined themes
        dirs, files = xbmcvfs.listdir(self.userThemesPath)
        for file in files:
            if file.endswith(".theme"):
                file = file.decode("utf-8")
                label = file.replace(".theme","")
                if label == activetheme and not self.daynight:
                    listlabel = label + " " + xbmc.getLocalizedString(461)
                else:
                    listlabel = label
                icon = os.path.join(self.userThemesPath,label + ".jpg")
                desc = "user defined theme"
                listitem = xbmcgui.ListItem(label=listlabel, iconImage=icon)
                listitem.setProperty("themename",label)
                listitem.setProperty("filename",self.userThemesPath+file)
                listitem.setProperty("description",desc)
                listitem.setProperty("Addon.Summary",desc)
                listitem.setLabel2(desc)
                listitem.setProperty("type","user")
                self.themesList.addItem(listitem)
        
        xbmc.sleep(150)
    
    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        if not xbmcvfs.exists(self.userThemesPath):
            xbmcvfs.mkdir(self.userThemesPath)
        
        self.themesList = self.getControl(6)
        
        self.getControl(1).setLabel(ADDON.getLocalizedString(32014))
        self.getControl(5).setVisible(True)
        self.getControl(3).setVisible(False)
        
        list = self.refreshListing()
        xbmc.executebuiltin("Control.SetFocus(6)")

    def onFocus(self, controlId):
        pass
        
    def onAction(self, action):

        ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
        ACTION_SHOW_INFO = ( 11, )
        ACTION_SELECT_ITEM = 7
        ACTION_PARENT_DIR = 9
        ACTION_CONTEXT_MENU = 117
        
        if action.getId() in ACTION_CANCEL_DIALOG:
            self.closeDialog()

    def closeDialog(self):
        self.close()
        
    def onClick(self, controlID):
                
        if(controlID == 6):
            item = self.themesList.getSelectedItem()
            type = item.getProperty("type")
            if type == "add":
                createColorTheme()
                self.refreshListing()
            elif type == "import":
                restoreColorTheme()
                self.refreshListing()
            else:
                themeFile = item.getProperty("filename").decode('utf-8')
                if self.daynight:
                    self.setDayNightTheme(item)
                else:
                    if type != "user":
                        #load skin provided theme
                        loadColorTheme(themeFile)
                    else:
                        #show contextmenu for user custom theme
                        menuOptions = []
                        menuOptions.append(ADDON.getLocalizedString(32083))
                        menuOptions.append(xbmc.getLocalizedString(117))
                        menuOptions.append(xbmc.getLocalizedString(118))
                        menuOptions.append(xbmc.getLocalizedString(19285))
                        menuOptions.append(ADDON.getLocalizedString(32019))
                        ret = xbmcgui.Dialog().select(item.getProperty("themename"), menuOptions)
                        if ret == 0:
                            loadColorTheme(themeFile)
                        elif ret == 1:
                            self.removeColorTheme(themeFile)
                        elif ret == 2:
                            self.renameColorTheme(themeFile,item.getProperty("themename"))
                        elif ret == 3:
                            self.setIconForColorTheme(themeFile)
                        elif ret == 4:
                            self.backupColorTheme(item.getLabel(),themeFile)
        elif(controlID == 5):
            self.closeDialog()

def loadColorTheme(file):
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    f = open(file,"r")
    importstring = json.load(f)
    f.close()
    skintheme = None
    skincolor = None
    skinfont = None
    currentSkinTheme = xbmc.getInfoLabel("Skin.CurrentTheme")
    
    currentSkinFont = None
    json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.font"}}')
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        if(jsonobject["result"].has_key('value')):
            currentSkinFont = jsonobject["result"]["value"]
    
    currentSkinColors = None
    json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"}}')
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        if(jsonobject["result"].has_key('value')):
            currentSkinColors = jsonobject["result"]["value"]
    
    settingslist = set()
    for count, skinsetting in enumerate(importstring):
        if skinsetting[0] == "SKINTHEME":
            skintheme = skinsetting[1].decode('utf-8')
        elif skinsetting[0] == "SKINCOLORS":
            skincolor = skinsetting[1]
        elif skinsetting[0] == "SKINFONT":
            skinfont = skinsetting[1]
        elif skinsetting[0] == "THEMENAME":
            xbmc.executebuiltin("Skin.SetString(SkinHelper.LastColorTheme,%s)" % skinsetting[1])
        elif skinsetting[0] == "DESCRIPTION":
            xbmc.executebuiltin("Skin.SetString(SkinHelper.LastColorTheme.Description,%s)" % try_encode(skinsetting[1]))
        elif skinsetting[1].startswith("SkinHelper.ColorTheme"): continue
        else:    
            #some legacy..
            setting = skinsetting[1]
            
            if setting.startswith("TITANSKIN"): setting = setting.replace("TITANSKIN.", "")
            if setting.startswith("."): setting = setting[1:]
            if not setting in settingslist:
                settingslist.add(setting)
                if skinsetting[0] == "string":
                    if skinsetting[2] is not "":
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" % (try_encode(setting), try_encode(skinsetting[2])))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % try_encode(setting))
                elif skinsetting[0] == "bool":
                    if skinsetting[2] == "true":
                        xbmc.executebuiltin("Skin.SetBool(%s)" % try_encode(setting))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % try_encode(setting))
                xbmc.sleep(30)
    
    #change the skintheme, color and font if needed 
    if skintheme and currentSkinTheme != skintheme:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"lookandfeel.skintheme","value":"%s"}}' %skintheme)
    if skincolor and currentSkinColors != skincolor:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"lookandfeel.skincolors","value":"%s"}}' %skincolor)
    if skinfont and currentSkinFont != skinfont and currentSkinFont.lower() != "arial":
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"lookandfeel.font","value":"%s"}}' %skinfont)

    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            
def get_browse_dialog(default="protocol://", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder,)
    return value

def restoreColorTheme():
    import zipfile
    zip_path = None
    userThemesPath = os.path.join(userThemesDir,"themes") + os.sep
    zip_path = get_browse_dialog(dlg_type=1,heading=ADDON.getLocalizedString(32082),mask=".zip")
    if zip_path and zip_path != "protocol://":
        #create temp path
        temp_path = xbmc.translatePath('special://temp/skinbackup/').decode("utf-8")
        if xbmcvfs.exists(temp_path):
            recursiveDelete(temp_path)
        xbmcvfs.mkdir(temp_path)
        
        #unzip to temp
        if "\\" in zip_path:
            delim = "\\"
        else:
            delim = "/"
        
        zip_temp = xbmc.translatePath('special://temp/' + zip_path.split(delim)[-1]).decode("utf-8")
        xbmcvfs.copy(zip_path,zip_temp)
        zfile = zipfile.ZipFile(zip_temp)
        zfile.extractall(temp_path)
        zfile.close()
        xbmcvfs.delete(zip_temp)
        
        dirs, files = xbmcvfs.listdir(temp_path)
        for file in files:
            if file.endswith(".theme") or file.endswith(".jpg"):
                sourcefile = os.path.join(temp_path,file)
                destfile = os.path.join(userThemesPath,file)
                xbmcvfs.copy(sourcefile,destfile)
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32022), ADDON.getLocalizedString(32021))
        
def createColorTheme():

    try:
        userThemesPath = os.path.join(userThemesDir,"themes") + os.sep   
        
        currentSkinFont = None
        json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.font"}}')
        jsonobject = json.loads(json_response.decode('utf-8','replace'))
        if(jsonobject.has_key('result')):
            if(jsonobject["result"].has_key('value')):
                currentSkinFont = jsonobject["result"]["value"]
        
        currentSkinColors = None
        json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"}}')
        jsonobject = json.loads(json_response.decode('utf-8','replace'))
        if(jsonobject.has_key('result')):
            if(jsonobject["result"].has_key('value')):
                currentSkinColors = jsonobject["result"]["value"]
        
        
        #user has to enter name for the theme
        dialog = xbmcgui.Dialog()
        themeName = dialog.input(ADDON.getLocalizedString(32023), type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
        if not themeName:
            return
        
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        xbmc.executebuiltin("Skin.SetString(SkinHelper.LastColorTheme,%s)" %themeName.encode("utf-8"))    
        
        #add screenshot
        dialog = xbmcgui.Dialog()
        custom_thumbnail = dialog.browse( 2 , ADDON.getLocalizedString(32024), 'files')
        
        if custom_thumbnail:
            xbmcvfs.copy(custom_thumbnail, os.path.join(userThemesPath, themeName + ".jpg"))

        #read the guisettings file to get all skin settings
        import BackupRestore as backup
        newlist = backup.getSkinSettings(["color","opacity","texture","panel","colour"])
        if newlist:
            newlist.append(("THEMENAME", themeName))
            newlist.append(("DESCRIPTION", ADDON.getLocalizedString(32025)))
            newlist.append(("SKINTHEME", xbmc.getInfoLabel("Skin.CurrentTheme")))
            newlist.append(("SKINFONT", currentSkinFont))
            newlist.append(("SKINCOLORS", currentSkinColors))
                
            #save guisettings
            text_file_path = os.path.join(userThemesPath, themeName + ".theme")
            text_file = xbmcvfs.File(text_file_path, "w")
            json.dump(newlist, text_file)
            text_file.close()
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32026), ADDON.getLocalizedString(32027))
    except Exception as e:
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32030), str(e))
  
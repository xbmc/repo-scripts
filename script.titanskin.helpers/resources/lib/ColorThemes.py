import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os, sys
import urllib
import threading
import InfoDialog
import json
from xml.dom.minidom import parse
from operator import itemgetter

addon = xbmcaddon.Addon(id='script.titanskin.helpers')
addondir = xbmc.translatePath(addon.getAddonInfo('profile'))

class ColorThemes(xbmcgui.WindowXMLDialog):

    themesList = None
    userThemesPath = None
    skinThemesPath = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
        self.userThemesPath = os.path.join(addondir,"themes") + os.sep
        self.skinThemesPath = xbmc.translatePath("special://skin/extras/skinthemes")

        
    def loadColorTheme(self,file):
        f = open(file,"r")
        importstring = json.load(f)
        f.close()
        
        currentSkinTheme = xbmc.getInfoLabel("Skin.CurrentTheme")
        
        for count, skinsetting in enumerate(importstring):
            if skinsetting[0] == ("SKINTHEME"):
                skintheme = skinsetting[1]
            if skinsetting[1].startswith("TITANSKIN"):
                setting = skinsetting[1].replace("TITANSKIN" + ".", "")
                if skinsetting[0] == "string":
                    if skinsetting[2] is not "":
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" % (setting, skinsetting[2]))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % setting)
                elif skinsetting[0] == "bool":
                    if skinsetting[2] == "true":
                        xbmc.executebuiltin("Skin.SetBool(%s)" % setting)
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % setting)
            xbmc.sleep(30)
        
        #change the skintheme if needed
        if currentSkinTheme != skintheme:
            xbmc.executebuiltin("Skin.Theme(-1)")

    def backupColorTheme(self, themeName, themeFile):
        import zipfile
        backup_path = get_browse_dialog(dlg_type=3,heading=xbmc.getLocalizedString(31283))
        
        if backup_path:
            backup_name = "TITANSKIN_COLORTHEME_" + themeName
            backup_path = os.path.join(backup_path,backup_name)
            backup_path_temp = xbmc.translatePath('special://temp/' + backup_name)
            
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
       
    
    def removeColorTheme(self,file):
        file = file.split(os.sep)[-1]
        themeName = file.replace(".theme","")
        xbmcvfs.delete(os.path.join(self.userThemesPath,themeName + ".jpg"))
        xbmcvfs.delete(os.path.join(self.userThemesPath,themeName + ".theme"))
        self.refreshListing()
        
    def renameColorTheme(self,file):
        file = file.split(os.sep)[-1]
        themeNameOld = file.replace(".theme","")
        
        dialog = xbmcgui.Dialog()
        themeNameNew = dialog.input('Enter a name for the theme', themeNameOld, type=xbmcgui.INPUT_ALPHANUM)
        if not themeNameNew:
            return
        
        xbmcvfs.rename(os.path.join(self.userThemesPath,themeNameOld + ".jpg"), os.path.join(self.userThemesPath,themeNameNew + ".jpg"))
        xbmcvfs.rename(os.path.join(self.userThemesPath,themeNameOld + ".theme"), os.path.join(self.userThemesPath,themeNameNew + ".theme"))
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
        count = 0
        
        #clear list first
        self.themesList.reset()
        
        #get all skin defined themes
        dirs, files = xbmcvfs.listdir(self.skinThemesPath)
        for file in files:
            if file.endswith(".theme"):
                icon = os.path.join(self.skinThemesPath,file.replace(".theme",".jpg"))
                f = open(os.path.join(self.skinThemesPath,file),"r")
                importstring = json.load(f)
                f.close()
                for count, skinsetting in enumerate(importstring):
                    if skinsetting[0] == ("DESCRIPTION"):
                        desc = skinsetting[1]
                    if skinsetting[0] == ("THEMENAME"):
                        label = skinsetting[1]

                listitem = xbmcgui.ListItem(label=label, iconImage=icon)
                listitem.setProperty("filename",os.path.join(self.skinThemesPath,file))
                listitem.setProperty("description",desc)
                listitem.setProperty("type","skin")
                self.themesList.addItem(listitem)
                count += 1
        
        #get all user defined themes
        dirs, files = xbmcvfs.listdir(self.userThemesPath)
        for file in files:
            if file.endswith(".theme"):
                label = file
                label = file.replace(".theme","")
                icon = os.path.join(self.userThemesPath,label + ".jpg")
                desc = "user defined theme"
                listitem = xbmcgui.ListItem(label=label, iconImage=icon)
                listitem.setProperty("filename",os.path.join(self.userThemesPath,file))
                listitem.setProperty("description",desc)
                listitem.setProperty("type","user")
                self.themesList.addItem(listitem)
                count += 1
        
        return count
    
    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        if not xbmcvfs.exists(self.userThemesPath):
            xbmcvfs.mkdir(self.userThemesPath)
        
        self.themesList = self.getControl(6)
        
        list = self.refreshListing()
        if list != 0:
            xbmc.executebuiltin("Control.SetFocus(6)")
        else:
            xbmc.executebuiltin("Control.SetFocus(5)")

    def onFocus(self, controlId):
        pass
        
    def onAction(self, action):

        ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, 1)
        ACTION_SHOW_INFO = ( 11, )
        ACTION_SELECT_ITEM = 7
        ACTION_PARENT_DIR = 9
        ACTION_CONTEXT_MENU = 117
        
        if action.getId() in ACTION_CANCEL_DIALOG:
            self.closeDialog()
        if action.getId() == ACTION_CONTEXT_MENU:
            dialog = xbmcgui.Dialog()
            item = self.themesList.getSelectedItem()
            themeFile = item.getProperty("filename")
            menuOptions = []
            menuOptions.append(xbmc.getLocalizedString(424))
            themeType = item.getProperty("type")
            if themeType == "user":
                menuOptions.append(xbmc.getLocalizedString(117))
                menuOptions.append(xbmc.getLocalizedString(118))
                menuOptions.append(xbmc.getLocalizedString(19285))
                menuOptions.append(xbmc.getLocalizedString(31542))
            ret = dialog.select(xbmc.getLocalizedString(33063), menuOptions)
            if ret == 0:
                self.loadColorTheme(themeFile)
            elif ret == 1:
                self.removeColorTheme(themeFile)
            elif ret == 2:
                self.renameColorTheme(themeFile)
            elif ret == 3:
                self.setIconForColorTheme(themeFile)
            elif ret == 4:
                self.backupColorTheme(item.getLabel(),themeFile) 

    def closeDialog(self):
        #self.close() ##crashes kodi ?
        xbmc.executebuiltin("Dialog.Close(all,true)")
        
    def onClick(self, controlID):
                
        if(controlID == 6):
            item = self.themesList.getSelectedItem()
            themeFile = item.getProperty("filename")
            self.loadColorTheme(themeFile)


def get_browse_dialog(default="protocol://", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)
    return value

def restoreColorTheme():
    import shutil
    import zipfile
    zip_path = None
    userThemesPath = os.path.join(addondir,"themes") + os.sep
    zip_path = get_browse_dialog(dlg_type=1,heading=xbmc.getLocalizedString(31282),mask=".zip")
    if zip_path:
        #create temp path
        temp_path = xbmc.translatePath('special://temp/skinbackup/').decode("utf-8")
        if xbmcvfs.exists(temp_path):
            shutil.rmtree(temp_path)
        xbmcvfs.mkdir(temp_path)
        
        #unzip to temp
        if "\\" in zip_path:
            delim = "\\"
        else:
            delim = "/"
        
        zip_temp = xbmc.translatePath('special://temp/' + zip_path.split(delim)[-1])
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
        xbmcgui.Dialog().ok(xbmc.getLocalizedString(31541), xbmc.getLocalizedString(31540))
        
def createColorTheme():
    userThemesPath = os.path.join(addondir,"themes") + os.sep    
    #user has to enter name for the theme
    dialog = xbmcgui.Dialog()
    themeName = dialog.input(xbmc.getLocalizedString(31467), type=xbmcgui.INPUT_ALPHANUM)
    if not themeName:
        return
    
    #add screenshot
    dialog = xbmcgui.Dialog()
    custom_thumbnail = dialog.browse( 2 , xbmc.getLocalizedString(31468), 'files')
    
    if custom_thumbnail:
        xbmcvfs.copy(custom_thumbnail, os.path.join(userThemesPath, themeName + ".jpg"))

    #read the guisettings file to get all skin settings
    from xml.dom.minidom import parse
    guisettings_path = xbmc.translatePath('special://profile/guisettings.xml').decode("utf-8")
    if xbmcvfs.exists(guisettings_path):
        doc = parse(guisettings_path)
        skinsettings = doc.documentElement.getElementsByTagName('setting')
        newlist = []
        newlist.append(("THEMENAME", themeName))
        newlist.append(("DESCRIPTION", xbmc.getLocalizedString(31466)))
        newlist.append(("SKINTHEME", xbmc.getInfoLabel("Skin.CurrentTheme")))

        for count, skinsetting in enumerate(skinsettings):
            if skinsetting.childNodes:
                value = skinsetting.childNodes[0].nodeValue
            else:
                value = ""
            
            #only get properties from the titan skin
            if skinsetting.attributes['name'].nodeValue.startswith(xbmc.getSkinDir() + "."):
                name = skinsetting.attributes['name'].nodeValue
                if "color" in name.lower() or "opacity" in name.lower() or "texture" in name.lower():
                    name = name.replace(xbmc.getSkinDir(),"TITANSKIN")
                    newlist.append((skinsetting.attributes['type'].nodeValue, name, value))
            
        #save guisettings
        text_file_path = os.path.join(userThemesPath, themeName + ".theme")
        text_file = xbmcvfs.File(text_file_path, "w")
        json.dump(newlist, text_file)
        text_file.close()
        
        xbmcgui.Dialog().ok(xbmc.getLocalizedString(31539), xbmc.getLocalizedString(31540))
        
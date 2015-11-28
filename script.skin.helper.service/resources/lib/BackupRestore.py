from Utils import *
import random
from xml.dom.minidom import parse


def getSkinSettings(filter=None):
    newlist = []
    if KODI_VERSION < 16:
        guisettings_path = xbmc.translatePath('special://profile/guisettings.xml').decode("utf-8")
    else:
        #workaround - reload skin to get guisettings
        xbmc.executebuiltin("Reloadskin")
        xbmc.sleep(1500)
        guisettings_path = xbmc.translatePath('special://profile/addon_data/%s/settings.xml' %xbmc.getSkinDir()).decode("utf-8")
    if xbmcvfs.exists(guisettings_path):
        logMsg("guisettings.xml found")
        doc = parse(guisettings_path)
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
                if settingname.endswith(".beta") or settingname.endswith(".helix"):
                    continue
                if not filter:
                    newlist.append((skinsetting.attributes['type'].nodeValue, settingname, settingvalue))
                else:
                    #filter
                    for filteritem in filter:
                        if filteritem.lower() in settingname.lower():
                            newlist.append((skinsetting.attributes['type'].nodeValue, settingname, settingvalue))
    else:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32030))
        logMsg("skin settings file not found")
    
    return newlist

def backup(filterString="",silent=None,promptfilename="false"):
    error = False
    try:
        if filterString:
            if "|" in filterString:
                filter = filterString.split("|")
            else:
                filter = []
                filter.append(filterString)
        else:
            filter = None

        #get backup destination
        backup_path = silent
        if not backup_path:
            backup_path = get_browse_dialog(dlg_type=3,heading=ADDON.getLocalizedString(32018)).decode("utf-8")
            if not backup_path or backup_path=="protocol://": return
        if promptfilename == "true":
            dialog = xbmcgui.Dialog()
            backup_name = dialog.input(ADDON.getLocalizedString(32068), type=xbmcgui.INPUT_ALPHANUM)
            if not backup_name: return
        else:
            from datetime import datetime
            i = datetime.now()
            backup_name = xbmc.getSkinDir().decode('utf-8').replace("skin.","") + "_SKIN_BACKUP_" + i.strftime('%Y%m%d-%H%M')
            
        if backup_path and backup_path != "protocol://":
            
                #get the skinsettings
                newlist = getSkinSettings(filter)

                if not xbmcvfs.exists(backup_path) and not silent:
                    xbmcvfs.mkdir(backup_path)
                
                #create temp path
                temp_path = xbmc.translatePath('special://temp/skinbackup/').decode("utf-8")
                if xbmcvfs.exists(temp_path):
                    recursiveDelete(temp_path)
                xbmcvfs.mkdir(temp_path)
                    
                #get skinshortcuts preferences
                skinshortcuts_path = temp_path + "skinshortcuts/"
                skinshortcuts_path_source = xbmc.translatePath('special://profile/addon_data/script.skinshortcuts/').decode("utf-8")
                logMsg(skinshortcuts_path_source)
                if xbmcvfs.exists(skinshortcuts_path_source) and (not filterString or filterString.lower() == "skinshortcutsonly"):
                    if not xbmcvfs.exists(skinshortcuts_path):
                        xbmcvfs.mkdir(skinshortcuts_path)
                    dirs, files = xbmcvfs.listdir(skinshortcuts_path_source)
                    for file in files:
                        sourcefile = skinshortcuts_path_source + file.decode("utf-8")
                        destfile = skinshortcuts_path + file.decode("utf-8")
                        logMsg("source --> " + sourcefile)
                        logMsg("destination --> " + destfile)

                        if file.endswith(".DATA.xml"):
                            xbmcvfs.copy(sourcefile,destfile)
                            #parse shortcuts file and look for any images - if found copy them to addon folder
                            doc = parse( destfile )
                            listing = doc.documentElement.getElementsByTagName( 'shortcut' )
                            for shortcut in listing:               
                                defaultID = shortcut.getElementsByTagName( 'defaultID' )
                                if defaultID:
                                    defaultID = defaultID[0].firstChild
                                    if defaultID:
                                        defaultID = defaultID.data
                                    if not defaultID: 
                                        defaultID = shortcut.getElementsByTagName( 'label' )[0].firstChild.data
                                    thumb = shortcut.getElementsByTagName( 'thumb' )
                                    if thumb:
                                        thumb = thumb[0].firstChild
                                        if thumb:
                                            thumb = thumb.data
                                            if thumb and(".jpg" in thumb.lower() or ".png" in thumb.lower()) and not xbmc.getSkinDir() in thumb and not thumb.startswith("$") and not thumb.startswith("androidapp"):
                                                thumb = getCleanImage(thumb) 
                                                extension = thumb.split(".")[-1]
                                                newthumb = os.path.join(skinshortcuts_path,"%s-thumb-%s.%s" %(xbmc.getSkinDir(),normalize_string(defaultID),extension))
                                                newthumb_vfs = "special://profile/addon_data/script.skinshortcuts/%s-thumb-%s.%s"%(xbmc.getSkinDir(),normalize_string(defaultID),extension)
                                                if xbmcvfs.exists(thumb):
                                                    xbmcvfs.copy(thumb,newthumb)
                                                    shortcut.getElementsByTagName( 'thumb' )[0].firstChild.data = newthumb_vfs
                            with open(destfile, 'w') as f:
                                f.write(doc.toxml(encoding='utf-8'))
                                                
                        elif file.endswith(".properties"):
                            if xbmc.getSkinDir() in file:
                                destfile = skinshortcuts_path + file.replace(xbmc.getSkinDir(), "SKINPROPERTIES")
                                xbmcvfs.copy(sourcefile,destfile)
                                #look for any backgrounds and translate them
                                with open(destfile, 'r') as f:
                                    data = f.read()
                                allprops = eval(data)
                                count = 0
                                for prop in allprops:
                                    if prop[2] == "background":
                                        background = prop[3]
                                        defaultID = prop[1]
                                        if background and (".jpg" in background.lower() or ".png" in background.lower()) and not xbmc.getSkinDir() in background and not background.startswith("$") and not background.startswith("androidapp"):
                                            background = getCleanImage(background)
                                            extension = background.split(".")[-1]
                                            newthumb = os.path.join(skinshortcuts_path,"%s-background-%s.%s" %(xbmc.getSkinDir(),normalize_string(defaultID),extension))
                                            newthumb_vfs = "special://profile/addon_data/script.skinshortcuts/%s-background-%s.%s"%(xbmc.getSkinDir(),normalize_string(defaultID),extension)
                                            if xbmcvfs.exists(background):
                                                xbmcvfs.copy(background,newthumb)
                                                allprops[count] = [prop[0],prop[1],prop[2],newthumb_vfs]
                                    if prop[2] == "backgroundName":
                                        background = prop[3]
                                        defaultID = prop[1]
                                        if "." in background and not background.startswith("special://") and not background.startswith("$") and not background.startswith("androidapp"):
                                            if "/" in background:
                                                delim = "/"
                                            else:
                                                delim = "\\"
                                            newthumb = background.split(delim)[-1]
                                            if xbmcvfs.exists(background):
                                                allprops[count] = [prop[0],prop[1],prop[2],newthumb]
                                    count += 1
                                with open(destfile, 'w') as f:
                                    f.write(repr(allprops))
                        else:
                            #just copy the remaining files
                            xbmcvfs.copy(sourcefile,destfile)
                        
                if not filterString.lower() == "skinshortcutsonly":
                    #save guisettings
                    text_file_path = os.path.join(temp_path, "guisettings.txt")
                    
                    with open(text_file_path, 'w') as f:
                        f.write(repr(newlist))
                
                #zip the backup
                zip_temp = xbmc.translatePath('special://temp/' + backup_name).decode("utf-8")
                zip(temp_path,zip_temp)
                
                if silent:
                    zip_final = silent
                else:
                    zip_final = backup_path + backup_name + ".zip"
                
                #copy to final location
                if xbmcvfs.exists(zip_final):
                    xbmcvfs.delete(zip_final)
                if not xbmcvfs.copy(zip_temp + ".zip", zip_final):
                    error = True
                    e = "Problem creating file in destination folder"
                
                #cleanup temp
                recursiveDelete(temp_path)
                xbmcvfs.delete(zip_temp + ".zip")

    except Exception as e:
        error = True
        
    if error:
        logMsg("ERROR while creating backup ! --> " + str(e), 0)            
        if not silent: xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32030), str(e))
    elif not silent:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32029))
        
def restore(silent=None):

    if silent and not xbmcvfs.exists(silent):
        logMsg("ERROR while creating backup ! --> Path invalid. Make sure you provide the FULL path, for example special://skin/extras/mybackup.zip", 0)
        return
    
    try:
        zip_path = silent
        progressDialog = None
        if not zip_path:
            zip_path = get_browse_dialog(dlg_type=1,heading=ADDON.getLocalizedString(32031),mask=".zip")
        
        if zip_path and zip_path != "protocol://":
            logMsg("zip_path " + zip_path)
            
            if not silent:
                progressDialog = xbmcgui.DialogProgress(ADDON.getLocalizedString(32032))
                progressDialog.create(ADDON.getLocalizedString(32032))
                progressDialog.update(0, "unpacking backup...")
            else:
                xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            
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
            unzip(zip_temp,temp_path)
            xbmcvfs.delete(zip_temp)
            
            #copy skinshortcuts preferences
            skinshortcuts_path_source = None
            if xbmcvfs.exists(temp_path + "skinshortcuts/"):
                
                skinshortcuts_path_source = temp_path + "skinshortcuts/"
                skinshortcuts_path_dest = xbmc.translatePath('special://profile/addon_data/script.skinshortcuts/').decode("utf-8")
                
                if xbmcvfs.exists(skinshortcuts_path_dest):
                   recursiveDelete(skinshortcuts_path_dest)
                xbmcvfs.mkdir(skinshortcuts_path_dest)
            
                dirs, files = xbmcvfs.listdir(skinshortcuts_path_source.encode("utf-8"))
                for file in files:
                    sourcefile = skinshortcuts_path_source.encode("utf-8") + file
                    destfile = skinshortcuts_path_dest.encode("utf-8") + file  
                    if file == "SKINPROPERTIES.properties":
                        destfile = skinshortcuts_path_dest + file.replace("SKINPROPERTIES",xbmc.getSkinDir())
                    logMsg("source --> " + sourcefile)
                    logMsg("destination --> " + destfile)
                    xbmcvfs.copy(sourcefile,destfile)
                        
            #read guisettings
            if xbmcvfs.exists(os.path.join(temp_path, "guisettings.txt")):
                text_file_path = os.path.join(temp_path, "guisettings.txt")
                with open(text_file_path, 'r') as f:
                    importstring = eval(f.read())
            
                xbmc.sleep(200)
                for count, skinsetting in enumerate(importstring):
                
                    if progressDialog:
                        if progressDialog.iscanceled():
                            return
                    setting = skinsetting[1]
                    settingvalue = skinsetting[2]
                    
                    #some legacy...
                    setting = setting.replace("TITANSKIN.helix", "").replace("TITANSKIN.", "")

                    try: setting = setting.encode('utf-8')
                    except: pass
                    
                    try: settingvalue = settingvalue.encode('utf-8')
                    except: pass

                    if progressDialog:
                        progressDialog.update((count * 100) / len(importstring), ADDON.getLocalizedString(32033) + ' %s' % setting.decode("utf-8"))

                    if skinsetting[0] == "string":
                        if settingvalue:
                            xbmc.executebuiltin("Skin.SetString(%s,%s)" % (setting, settingvalue))
                        else:
                            xbmc.executebuiltin("Skin.Reset(%s)" % setting)
                    elif skinsetting[0] == "bool":
                        if settingvalue == "true":
                            xbmc.executebuiltin("Skin.SetBool(%s)" % setting)
                        else:
                            xbmc.executebuiltin("Skin.Reset(%s)" % setting)
                    xbmc.sleep(30)
            
            #cleanup temp
            xbmc.sleep(500)
            recursiveDelete(temp_path)
            if not silent:
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32032), ADDON.getLocalizedString(32034))
            else:
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    
    except Exception as e:
        if not silent:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32032), ADDON.getLocalizedString(32035), str(e))
        logMsg("ERROR while restoring backup ! --> " + str(e), 0)
       
def reset():
    yeslabel=xbmc.getLocalizedString(107)
    nolabel=xbmc.getLocalizedString(106)
    dialog = xbmcgui.Dialog()
    
    ret = dialog.yesno(heading=ADDON.getLocalizedString(32036), line1=ADDON.getLocalizedString(32037), nolabel=nolabel, yeslabel=yeslabel)
    if ret:
        xbmc.executebuiltin("RunScript(script.skinshortcuts,type=resetall&warning=false)")
        xbmc.sleep(250)
        xbmc.executebuiltin("Skin.ResetSettings")
        xbmc.sleep(250)
        xbmc.executebuiltin("ReloadSkin")
             
def save_to_file(content, filename, path=""):
    if path == "":
        text_file_path = get_browse_dialog() + filename + ".txt"
    else:
        if not xbmcvfs.exists(path):
            xbmcvfs.mkdir(path)
        text_file_path = os.path.join(path, filename + ".txt")
    logMsg("save to textfile: " + text_file_path)
    text_file = xbmcvfs.File(text_file_path, "w")
    json.dump(content, text_file)
    text_file.close()
    return True

def read_from_file(path=""):
    if path == "":
        path = get_browse_dialog(dlg_type=1)
    if xbmcvfs.exists(path):
        f = open(path)
        fc = json.load(f)
        logMsg("loaded textfile " + path)
        return fc
    else:
        return False
       
def get_browse_dialog(default="protocol://", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder)
    return value
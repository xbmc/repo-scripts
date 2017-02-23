#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.skinbackup
    Kodi addon to backup skin settings
'''

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from utils import log_msg, log_exception, ADDON_ID, kodi_json, unzip_fromfile
from utils import recursive_delete_dir, get_clean_image, normalize_string, get_skin_name
from dialogselect import DialogSelect
from datetime import datetime
import time
import os


class ColorThemes():
    '''Allow the user to create custom colorthemes for the skin by creating backups of colorsettings for the skin'''

    def __init__(self):
        self.userthemes_path = u"special://profile/addon_data/%s/themes/" % xbmc.getSkinDir()
        if not xbmcvfs.exists(self.userthemes_path):
            xbmcvfs.mkdir(self.userthemes_path)
        self.skinthemes_path = u"special://skin/extras/skinthemes/"
        if xbmcvfs.exists("special://home/addons/resource.skinthemes.%s/resources/" % get_skin_name()):
            self.skinthemes_path = u"special://home/addons/resource.skinthemes.%s/resources/" % get_skin_name()
        self.addon = xbmcaddon.Addon(ADDON_ID)

    def __del__(self):
        '''Cleanup Kodi Cpython instances on exit'''
        del self.addon

    def colorthemes(self):
        '''show dialog with all available color themes'''
        listitems = []
        # create item
        listitem = xbmcgui.ListItem(label=self.addon.getLocalizedString(32035), iconImage="DefaultAddonSkin.png")
        listitem.setLabel2(self.addon.getLocalizedString(32036))
        listitem.setPath("add")
        listitems.append(listitem)
        # import item
        listitem = xbmcgui.ListItem(label=self.addon.getLocalizedString(32037), iconImage="DefaultAddonSkin.png")
        listitem.setLabel2(self.addon.getLocalizedString(32038))
        listitem.setPath("import")
        listitems.append(listitem)
        # get all skin and user defined themes
        listitems += self.get_skin_colorthemes()
        listitems += self.get_user_colorthemes()

        # show dialog and list options
        header = self.addon.getLocalizedString(32020)
        dialog = DialogSelect("DialogSelect.xml", "", windowtitle=header,
                              richlayout=True, listing=listitems)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            themefile = result.getfilename().decode("utf-8")
            themename = result.getLabel().decode("utf-8")
            has_icon = xbmcvfs.exists(themefile.replace(".theme", ".jpg"))
            if themefile == "add":
                # create new colortheme
                self.create_colortheme()
                self.colorthemes()
            elif themefile == "import":
                # import theme file
                self.restore_colortheme()
                self.colorthemes()
            elif self.skinthemes_path in themefile:
                # load skin provided theme
                self.load_colortheme(themefile)
            else:
                # show contextmenu for user custom theme
                menuoptions = []
                menuoptions.append(self.addon.getLocalizedString(32021))
                menuoptions.append(xbmc.getLocalizedString(117))
                if not has_icon:
                    menuoptions.append(xbmc.getLocalizedString(19285))
                menuoptions.append(self.addon.getLocalizedString(32022))
                ret = xbmcgui.Dialog().select(themename, menuoptions)
                if ret == 0:
                    self.load_colortheme(themefile)
                elif ret == 1:
                    self.remove_theme(themefile)
                elif ret == 2 and not has_icon:
                    self.set_icon_for_theme(themefile)
                elif ret == 3 or (ret == 2 and has_icon):
                    self.backup_theme(themename)
                if not ret == 0:
                    # show selection dialog again
                    self.colorthemes()

    def daynightthemes(self, dayornight):
        '''allow user to set a specific theme during day/night time'''

        if dayornight not in ["day", "night"]:
            log_msg("Invalid parameter for day/night theme - must be day or night")
            return

        # show listing with themes
        listitems = self.get_skin_colorthemes()
        listitems += self.get_user_colorthemes()
        header = self.addon.getLocalizedString(32031)
        curvalue = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.theme)" % dayornight).decode("utf-8")
        dialog = DialogSelect("DialogSelect.xml", "", windowtitle=header,
                              richlayout=True, listing=listitems, autofocus=curvalue)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            themefile = result.getfilename().decode("utf-8")
            themename = result.getLabel().decode("utf-8")
            self.set_day_night_theme(dayornight, themename, themefile)

    def set_day_night_theme(self, dayornight, themename, themefile):
        ''' Sets a new daynight theme'''
        currenttimevalue = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.time)" % dayornight)
        if not currenttimevalue:
            currenttimevalue = "20:00" if dayornight == "night" else "07:00"
        timevalue = xbmcgui.Dialog().input(self.addon.getLocalizedString(32017),
                                           currenttimevalue).decode("utf-8")
        try:
            # check if the time is valid
            check_date = datetime(*(time.strptime(timevalue, "%H:%M")[0:6]))
            del check_date
            base_setting = "SkinHelper.ColorTheme.%s" % dayornight
            xbmc.executebuiltin("Skin.SetString(%s.theme,%s)" % (base_setting, themename.encode("utf-8")))
            xbmc.executebuiltin("Skin.SetString(%s.time,%s)" % (base_setting, timevalue))
            label = "%s  (%s %s)" % (themename.encode("utf-8"), self.addon.getLocalizedString(32019), timevalue)
            xbmc.executebuiltin("Skin.SetString(%s.label,%s)" % (base_setting, label))
            xbmc.executebuiltin("Skin.SetString(%s.file,%s)" % (base_setting, themefile.encode("utf-8")))
        except Exception as exc:
            log_exception(__name__, exc)
            xbmcgui.Dialog().ok(xbmc.getLocalizedString(329), self.addon.getLocalizedString(32018))

    def backup_theme(self, themename):
        '''backup a colortheme to a zipfile'''
        import zipfile
        backup_path = xbmcgui.Dialog().browse(3, self.addon.getLocalizedString(32029), "files").decode("utf-8")
        if backup_path:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            backup_name = u"%s ColorTheme - %s" % (get_skin_name().capitalize(), themename)
            backupfile = os.path.join(backup_path, backup_name + u".zip")
            zip_temp = u'special://temp/%s.zip' % backup_name
            xbmcvfs.delete(zip_temp)
            xbmcvfs.delete(backupfile)
            zip_temp = xbmc.translatePath(zip_temp).decode("utf-8")
            zip_file = zipfile.ZipFile(zip_temp, "w", zipfile.ZIP_DEFLATED)
            abs_src = os.path.abspath(xbmc.translatePath(self.userthemes_path).decode("utf-8"))
            for filename in xbmcvfs.listdir(self.userthemes_path)[1]:
                if (filename.startswith("%s_" % themename) or
                        filename.replace(".theme", "").replace(".jpg", "") == themename):
                    filename = filename.decode("utf-8")
                    filepath = xbmc.translatePath(self.userthemes_path + filename).decode("utf-8")
                    absname = os.path.abspath(filepath)
                    arcname = absname[len(abs_src) + 1:]
                    zip_file.write(absname, arcname)
            zip_file.close()
            xbmcvfs.copy(zip_temp, backupfile)
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    @staticmethod
    def remove_theme(filename):
        '''remove theme from disk'''
        xbmcvfs.delete(filename.replace(".theme", ".jpg"))
        xbmcvfs.delete(filename)

    @staticmethod
    def set_icon_for_theme(filename):
        '''sets an icon for an existing theme'''
        iconpath = filename.replace(".theme", ".jpg")
        dialog = xbmcgui.Dialog()
        custom_thumbnail = dialog.browse(2, xbmc.getLocalizedString(1030), 'files')
        if custom_thumbnail:
            xbmcvfs.delete(iconpath)
            xbmcvfs.copy(custom_thumbnail, iconpath)

    @staticmethod
    def get_activetheme():
        '''get current active theme name'''
        return xbmc.getInfoLabel("$INFO[Skin.String(SkinHelper.LastColorTheme)]").decode("utf-8")

    def get_skin_colorthemes(self):
        '''returns all available skinprovided colorthemes as listitems'''
        listitems = []
        for file in xbmcvfs.listdir(self.skinthemes_path)[1]:
            if file.endswith(".theme"):
                file = file.decode("utf-8")
                themefile = self.skinthemes_path + file
                icon = themefile.replace(".theme", ".jpg")
                if not xbmcvfs.exists(icon):
                    icon = ""
                xbmcfile = xbmcvfs.File(themefile)
                data = xbmcfile.read()
                xbmcfile.close()
                for skinsetting in eval(data):
                    if skinsetting[0] == "DESCRIPTION":
                        desc = skinsetting[1]
                    if skinsetting[0] == "THEMENAME":
                        label = skinsetting[1]

                if label == self.get_activetheme():
                    desc = xbmc.getLocalizedString(461)
                listitem = xbmcgui.ListItem(label, iconImage=icon)
                listitem.setLabel2(desc)
                listitem.setPath(themefile)
                listitems.append(listitem)
        return listitems

    def get_user_colorthemes(self):
        '''get all user stored color themes as listitems'''
        listitems = []
        for file in xbmcvfs.listdir(self.userthemes_path)[1]:
            if file.endswith(".theme"):
                file = file.decode("utf-8")
                themefile = self.userthemes_path + file
                label = file.replace(".theme", "")
                icon = themefile.replace(".theme", ".jpg")
                if not xbmcvfs.exists(icon):
                    icon = ""
                desc = "user defined theme"
                if label == self.get_activetheme():
                    desc = xbmc.getLocalizedString(461)
                listitem = xbmcgui.ListItem(label, iconImage=icon)
                listitem.setLabel2(desc)
                listitem.setPath(themefile)
                listitems.append(listitem)
        return listitems

    @staticmethod
    def load_colortheme(filename):
        '''load colortheme from themefile'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        xbmcfile = xbmcvfs.File(filename)
        data = xbmcfile.read()
        xbmcfile.close()
        importstring = eval(data)
        skintheme = None
        skincolor = None
        skinfont = None
        current_skintheme = xbmc.getInfoLabel("Skin.CurrentTheme").decode("utf-8")

        current_skinfont = None
        json_response = kodi_json("Settings.GetSettingValue", {"setting": "lookandfeel.font"})
        if json_response:
            current_skinfont = json_response
        current_skincolors = None
        json_response = kodi_json("Settings.GetSettingValue", {"setting": "lookandfeel.skincolors"})
        if json_response:
            current_skincolors = json_response

        settingslist = set()
        for skinsetting in importstring:
            if skinsetting[0] == "SKINTHEME":
                skintheme = skinsetting[1].decode('utf-8')
            elif skinsetting[0] == "SKINCOLORS":
                skincolor = skinsetting[1]
            elif skinsetting[0] == "SKINFONT":
                skinfont = skinsetting[1]
            elif skinsetting[0] == "THEMENAME":
                xbmc.executebuiltin("Skin.SetString(SkinHelper.LastColorTheme,%s)" % skinsetting[1])
            elif skinsetting[0] == "DESCRIPTION":
                xbmc.executebuiltin(
                    "Skin.SetString(SkinHelper.LastColorTheme.Description,%s)" % skinsetting[1])
            elif skinsetting[1].startswith("SkinHelper.ColorTheme"):
                continue
            else:
                setting = skinsetting[1]
                if isinstance(setting, unicode):
                    setting = setting.encode("utf-8")
                if setting not in settingslist:
                    settingslist.add(setting)
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

        # change the skintheme, color and font if needed
        if skintheme and current_skintheme != skintheme:
            kodi_json("Settings.SetSettingValue", {"setting": "lookandfeel.skintheme", "value": skintheme})
        if skincolor and current_skincolors != skincolor:
            kodi_json("Settings.SetSettingValue", {"setting": "lookandfeel.skincolors", "value": skincolor})
        if skinfont and current_skinfont != skinfont and current_skinfont.lower() != "arial":
            kodi_json("Settings.SetSettingValue", {"setting": "lookandfeel.font", "value": skinfont})

        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def restore_colortheme(self):
        '''restore zipbackup of colortheme to colorthemes folder'''
        zip_path = xbmcgui.Dialog().browse(1, self.addon.getLocalizedString(32030), "files", ".zip")
        if zip_path and zip_path.endswith(".zip"):

            # create temp path
            temp_path = u'special://temp/skinbackup/'
            temp_zip = u"special://temp/colortheme.zip"
            if xbmcvfs.exists(temp_path):
                recursive_delete_dir(temp_path)
            xbmcvfs.mkdir(temp_path)

            # unzip to temp
            xbmcvfs.copy(zip_path, temp_zip)
            unzip_fromfile(temp_zip, temp_path)
            for filename in xbmcvfs.listdir(temp_path)[1]:
                filename = filename.decode("utf-8")
                sourcefile = os.path.join(temp_path, filename)
                destfile = os.path.join(self.userthemes_path, filename)
                xbmcvfs.copy(sourcefile, destfile)
            # cleanup temp
            xbmcvfs.delete(temp_zip)
            recursive_delete_dir(temp_path)
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32026), self.addon.getLocalizedString(32027))

    def create_colortheme(self):
        '''create a colortheme from current skin color settings'''
        try:
            current_skinfont = None
            json_response = kodi_json("Settings.GetSettingValue", {"setting": "lookandfeel.font"})
            if json_response:
                current_skinfont = json_response
            current_skincolors = None
            json_response = kodi_json("Settings.GetSettingValue", {"setting": "lookandfeel.skincolors"})
            if json_response:
                current_skincolors = json_response

            # user has to enter name for the theme
            themename = xbmcgui.Dialog().input(self.addon.getLocalizedString(32023),
                                               type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
            if not themename:
                return

            xbmc.executebuiltin("ActivateWindow(busydialog)")
            xbmc.executebuiltin("Skin.SetString(SkinHelper.LastColorTheme,%s)" % themename.encode("utf-8"))

            # add screenshot
            custom_thumbnail = xbmcgui.Dialog().browse(2, self.addon.getLocalizedString(32024), 'files')

            if custom_thumbnail:
                xbmcvfs.copy(custom_thumbnail, self.userthemes_path + themename + ".jpg")

            # read the guisettings file to get all skin settings
            from backuprestore import BackupRestore
            skinsettingslist = BackupRestore().get_skinsettings(
                ["color", "opacity", "texture", "panel", "colour", "background", "image"])
            newlist = []
            if skinsettingslist:
                newlist.append(("THEMENAME", themename))
                newlist.append(("DESCRIPTION", self.addon.getLocalizedString(32025)))
                newlist.append(("SKINTHEME", xbmc.getInfoLabel("Skin.CurrentTheme")))
                newlist.append(("SKINFONT", current_skinfont))
                newlist.append(("SKINCOLORS", current_skincolors))

                # look for any images in the skin settings and translate them so they can
                # be included in the theme backup
                for skinsetting in skinsettingslist:
                    setting_type = skinsetting[0]
                    setting_name = skinsetting[1]
                    setting_value = skinsetting[2]
                    if setting_type == "string" and setting_value:
                        if (setting_value and (setting_value.endswith(".png") or
                                               setting_value.endswith(".gif") or
                                               setting_value.endswith(".jpg")) and
                                "resource://" not in setting_value):
                            image = get_clean_image(setting_value)
                            extension = image.split(".")[-1]
                            newimage = "%s_%s.%s" % (themename, normalize_string(setting_name), extension)
                            newimage_path = self.userthemes_path + newimage
                            if xbmcvfs.exists(image):
                                xbmcvfs.copy(image, newimage_path)
                                skinsetting = (setting_type, setting_name, newimage_path)
                    newlist.append(skinsetting)

                # save guisettings
                text_file_path = self.userthemes_path + themename + ".theme"
                text_file = xbmcvfs.File(text_file_path, "w")
                text_file.write(repr(newlist))
                text_file.close()
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmcgui.Dialog().ok(self.addon.getLocalizedString(32026), self.addon.getLocalizedString(32027))
        except Exception as exc:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            log_exception(__name__, exc)
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(32028), self.addon.getLocalizedString(32030), str(exc))

    def check_daynighttheme(self):
        '''check if a specific day or night theme should be applied'''
        if xbmc.getCondVisibility(
                "Skin.HasSetting(SkinHelper.EnableDayNightThemes) + "
                "Skin.String(SkinHelper.ColorTheme.Day.time) + "
                "Skin.String(SkinHelper.ColorTheme.Night.time)"):
            try:
                daytime = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.Day.time)")
                daytime = datetime(*(time.strptime(daytime, "%H:%M")[0:6])).time()
                nighttime = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.Night.time)")
                nighttime = datetime(*(time.strptime(nighttime, "%H:%M")[0:6])).time()
                timestamp = datetime.now().time()
                if daytime <= timestamp <= nighttime:
                    dayornight = "Day"
                else:
                    dayornight = "Night"
                current_theme = xbmc.getInfoLabel("Skin.String(SkinHelper.LastColorTheme)")
                newtheme = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.theme)" % dayornight)
                if current_theme != newtheme:
                    themefile = xbmc.getInfoLabel("Skin.String(SkinHelper.ColorTheme.%s.file)" % dayornight)
                    self.load_colortheme(themefile)
            except Exception as exc:
                log_exception(__name__, exc)

#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    skinsettings.py
    several helpers that allows skinners to have custom dialogs for their skin settings and constants
'''

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from utils import ADDON_ID, try_decode
from dialogselect import DialogSelect
from xml.dom.minidom import parse
import xml.etree.ElementTree as xmltree
import os
import time


class SkinSettings:
    '''several helpers that allows skinners to have custom dialogs for their skin settings and constants'''
    params = {}
    skinsettings = {}

    def __init__(self):
        '''Initialization'''
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.skinsettings = self.get_skin_settings()
        self.skin_constants, self.skin_variables = self.get_skin_constants()

    def __del__(self):
        '''Cleanup Kodi Cpython instances'''
        del self.win
        del self.addon

    def write_skin_constants(self, constants=None, variables=None):
        '''writes the list of all skin constants'''
        addonpath = xbmc.translatePath(os.path.join("special://skin/", 'addon.xml').encode("utf-8")).decode("utf-8")
        addon = xmltree.parse(addonpath)
        extensionpoints = addon.findall("extension")
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    includes_file = xbmc.translatePath(
                        os.path.join(
                            "special://skin/",
                            try_decode(
                                resolution.attrib.get("folder")),
                            "script-skin_helper_service-includes.xml").encode("utf-8")).decode('utf-8')
                    tree = xmltree.ElementTree(xmltree.Element("includes"))
                    root = tree.getroot()
                    if constants:
                        for key, value in constants.iteritems():
                            if value:
                                child = xmltree.SubElement(root, "constant")
                                child.text = value
                                child.attrib["name"] = key
                                # also write to skin strings
                                xbmc.executebuiltin(
                                    "Skin.SetString(%s,%s)" %
                                    (key.encode("utf-8"), value.encode("utf-8")))
                    if variables:
                        for key, value in variables.iteritems():
                            if value:
                                child = xmltree.SubElement(root, "variable")
                                child.attrib["name"] = key
                                child2 = xmltree.SubElement(child, "value")
                                child2.text = value
                    self.indent_xml(tree.getroot())
                    xmlstring = xmltree.tostring(tree.getroot(), encoding="utf-8")
                    fileobj = xbmcvfs.File(includes_file, 'w')
                    fileobj.write(xmlstring)
                    fileobj.close()
        xbmc.executebuiltin("ReloadSkin()")

    @staticmethod
    def get_skin_constants():
        '''gets a list of all skin constants as set in the special xml file'''
        all_constants = {}
        all_variables = {}
        addonpath = xbmc.translatePath(os.path.join("special://skin/", 'addon.xml').encode("utf-8")).decode("utf-8")
        addon = xmltree.parse(addonpath)
        extensionpoints = addon.findall("extension")
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    includes_file = xbmc.translatePath(
                        os.path.join(
                            "special://skin/",
                            try_decode(
                                resolution.attrib.get("folder")),
                            "script-skin_helper_service-includes.xml").encode("utf-8")).decode('utf-8')
                    if xbmcvfs.exists(includes_file):
                        doc = parse(includes_file)
                        listing = doc.documentElement.getElementsByTagName('constant')
                        # constants
                        for item in listing:
                            name = try_decode(item.attributes['name'].nodeValue)
                            value = try_decode(item.firstChild.nodeValue)
                            all_constants[name] = value
                        # variables
                        listing = doc.documentElement.getElementsByTagName('variable')
                        for item in listing:
                            name = try_decode(item.attributes['name'].nodeValue)
                            value_item = item.getElementsByTagName('value')[0]
                            value = try_decode(value_item.firstChild.nodeValue)
                            all_variables[name] = value
        return all_constants, all_variables

    def update_skin_constants(self, new_constants):
        '''update skin constants if needed'''
        update_needed = False
        if new_constants:
            for key, value in new_constants.iteritems():
                if key in self.skin_constants:
                    if self.skin_constants.get(key) != value:
                        update_needed = True
                        self.skin_constants[key] = value
                else:
                    update_needed = True
                    self.skin_constants[key] = value
        if update_needed:
            self.write_skin_constants(self.skin_constants, self.skin_variables)

    def set_skin_constant(self, setting="", window_header="", value=""):
        '''set a skin constant'''
        cur_values = self.skin_constants
        if not value:
            cur_value = cur_values.get(setting, "emptyconstant")
            value = self.set_skin_setting(setting, window_header, "", cur_value)[0]
        result = {setting: value}
        self.update_skin_constants(result)

    def set_skin_constants(self, settings, values):
        '''set multiple constants at once'''
        result = {}
        for count, setting in enumerate(settings):
            result[setting] = values[count]
        self.update_skin_constants(result)

    def set_skin_variable(self, key, value):
        '''set skin variable in constants file'''
        if self.skin_variables.get(key, "") != value:
            self.skin_variables[key] = value
            self.write_skin_constants(self.skin_constants, self.skin_variables)

    @staticmethod
    def get_skin_settings():
        '''get the complete list of all settings defined in the special skinsettings file'''
        all_skinsettings = {}
        settings_file = xbmc.translatePath('special://skin/extras/skinsettings.xml').decode("utf-8")
        if xbmcvfs.exists(settings_file):
            doc = parse(settings_file)
            listing = doc.documentElement.getElementsByTagName('setting')
            for item in listing:
                skinsetting_id = item.attributes["id"].nodeValue.decode("utf-8")
                if "$" in skinsetting_id:
                    skinsetting_id = xbmc.getInfoLabel(skinsetting_id).decode("utf-8")
                if all_skinsettings.get(skinsetting_id):
                    skinsetting_values = all_skinsettings[skinsetting_id]
                else:
                    skinsetting_values = []
                skinsettingvalue = {}
                skinsettingvalue["value"] = item.attributes["value"].nodeValue.decode("utf-8")
                # optional attributes
                for key in ["label", "condition", "description", "default", "icon", "constantdefault"]:
                    value = ""
                    try:
                        value = item.attributes[key].nodeValue
                        if "$" in value:
                            value = xbmc.getInfoLabel(value).decode("utf-8")
                        else:
                            value = value.decode("utf-8")
                    except Exception:
                        pass
                    skinsettingvalue[key] = value

                # optional onselect actions for this skinsetting value
                onselectactions = []
                for action in item.getElementsByTagName('onselect'):
                    selectaction = {}
                    selectaction["condition"] = action.attributes['condition'].nodeValue.decode("utf-8")
                    command = action.firstChild.nodeValue
                    if "$" in command:
                        command = xbmc.getInfoLabel(command).decode("utf-8")
                    else:
                        command = command.decode("utf-8")
                    selectaction["command"] = command
                    onselectactions.append(selectaction)
                skinsettingvalue["onselectactions"] = onselectactions

                # optional multiselect options for this skinsetting value
                settingoptions = []
                for option in item.getElementsByTagName('option'):
                    settingoption = {}
                    for key in ["id", "label", "condition", "description", "default", "icon", "value"]:
                        value = ""
                        try:
                            value = option.attributes[key].nodeValue
                            if value.startswith("$"):
                                value = xbmc.getInfoLabel(value).decode("utf-8")
                            else:
                                value = value.decode("utf-8")
                        except Exception:
                            pass
                        settingoption[key] = value
                    settingoptions.append(settingoption)
                skinsettingvalue["settingoptions"] = settingoptions

                skinsetting_values.append(skinsettingvalue)
                all_skinsettings[skinsetting_id] = skinsetting_values
        return all_skinsettings

    def set_skin_setting(self, setting="", window_header="", sublevel="",
                         cur_value_label="", skip_skin_string=False, original_id="", cur_value=""):
        '''allows the skinner to use a select dialog to set all kind of skin settings'''
        if not cur_value_label:
            cur_value_label = xbmc.getInfoLabel("Skin.String(%s.label)" % setting).decode("utf-8")
        if not cur_value:
            cur_value = xbmc.getInfoLabel("Skin.String(%s)" % setting).decode("utf-8")
        rich_layout = False
        listitems = []
        if sublevel:
            listitem = xbmcgui.ListItem(label="..", iconImage="DefaultFolderBack.png")
            listitem.setProperty("icon", "DefaultFolderBack.png")
            listitem.setProperty("value", "||BACK||")
            listitems.append(listitem)
            all_values = self.skinsettings.get(sublevel, [])
        elif original_id:
            all_values = self.skinsettings.get(original_id, [])
        else:
            all_values = self.skinsettings.get(setting, [])
        for item in all_values:
            if not item["condition"] or xbmc.getCondVisibility(item["condition"]):
                value = item["value"]
                icon = item["icon"]
                if icon:
                    rich_layout = True
                label = item["label"]
                if "%" in label:
                    label = label % value
                if value == "||MULTISELECT||" or item["settingoptions"]:
                    return self.multi_select(item["settingoptions"], window_header)
                listitem = xbmcgui.ListItem(label, iconImage=icon, label2=item["description"])
                listitem.setProperty("value", value)
                listitem.setProperty("icon", icon)
                listitem.setProperty("description", item["description"])
                listitem.setProperty("onselectactions", repr(item["onselectactions"]))
                listitems.append(listitem)

        # show select dialog
        dialog = DialogSelect("DialogSelect.xml", "", listing=listitems, windowtitle=window_header,
                              richlayout=rich_layout, autofocuslabel=cur_value_label)
        dialog.doModal()
        selected_item = dialog.result
        del dialog
        # process the results
        if selected_item:
            value = selected_item.getProperty("value").decode("utf-8")
            label = selected_item.getLabel().decode("utf-8")
            if value.startswith("||SUBLEVEL||"):
                sublevel = value.replace("||SUBLEVEL||", "")
                self.set_skin_setting(setting, window_header, sublevel)
            elif value == "||BACK||":
                self.set_skin_setting(setting, window_header)
            else:
                if value == "||BROWSEIMAGE||":
                    value = self.save_skin_image(setting, True, label)
                if value == "||BROWSESINGLEIMAGE||":
                    value = self.save_skin_image(setting, False, label)
                if value == "||BROWSEMULTIIMAGE||":
                    value = self.save_skin_image(setting, True, label)
                if value == "||PROMPTNUMERIC||":
                    value = xbmcgui.Dialog().input(label, cur_value, 1).decode("utf-8")
                if value == "||PROMPTSTRING||":
                    value = xbmcgui.Dialog().input(label, cur_value, 0).decode("utf-8")
                if value == "||PROMPTSTRINGASNUMERIC||":
                    validinput = False
                    while not validinput:
                        try:
                            value = xbmcgui.Dialog().input(label, cur_value, 0).decode("utf-8")
                            valueint = int(value)
                            validinput = True
                            del valueint
                        except Exception:
                            value = xbmcgui.Dialog().notification("Invalid input", "Please enter a number...")

                # write skin strings
                if not skip_skin_string and value != "||SKIPSTRING||":
                    xbmc.executebuiltin("Skin.SetString(%s,%s)" %
                                        (setting.encode("utf-8"), value.encode("utf-8")))
                    xbmc.executebuiltin("Skin.SetString(%s.label,%s)" %
                                        (setting.encode("utf-8"), label.encode("utf-8")))
                # process additional actions
                onselectactions = selected_item.getProperty("onselectactions")
                if onselectactions:
                    for action in eval(onselectactions):
                        if not action["condition"] or xbmc.getCondVisibility(action["condition"]):
                            xbmc.executebuiltin(action["command"])
                return (value, label)
        else:
            return (None, None)

    def correct_skin_settings(self):
        '''correct any special skin settings'''
        skinconstants = {}
        for settingid, settingvalues in self.skinsettings.iteritems():
            curvalue = xbmc.getInfoLabel("Skin.String(%s)" % settingid).decode("utf-8")
            curlabel = xbmc.getInfoLabel("Skin.String(%s.label)" % settingid).decode("utf-8")
            # first check if we have a sublevel
            if settingvalues and settingvalues[0]["value"].startswith("||SUBLEVEL||"):
                sublevel = settingvalues[0]["value"].replace("||SUBLEVEL||", "")
                settingvalues = self.skinsettings.get(sublevel)
            for settingvalue in settingvalues:
                value = settingvalue["value"]
                label = settingvalue["label"]
                if "%" in label:
                    label = label % value

                # only correct the label if value already set
                if value and value == curvalue:
                    xbmc.executebuiltin(
                        "Skin.SetString(%s.label,%s)" %
                        (settingid.encode("utf-8"), label.encode("utf-8")))

                # set the default value if current value is empty
                if not (curvalue or curlabel):
                    if settingvalue["default"] and xbmc.getCondVisibility(settingvalue["default"]):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s.label,%s)" %
                            (settingid.encode("utf-8"), label.encode("utf-8")))
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (settingid.encode("utf-8"), value.encode("utf-8")))
                        # additional onselect actions
                        for action in settingvalue["onselectactions"]:
                            if action["condition"] and xbmc.getCondVisibility(action["condition"]):
                                command = action["command"]
                                if "$" in command:
                                    command = xbmc.getInfoLabel(command)
                                xbmc.executebuiltin(command.encode("utf-8"))

                # process any multiselects
                for option in settingvalue["settingoptions"]:
                    settingid = option["id"]
                    if (not xbmc.getInfoLabel("Skin.String(defaultset_%s)" % settingid) and option["default"] and
                            xbmc.getCondVisibility(option["default"])):
                        xbmc.executebuiltin("Skin.SetBool(%s)" % settingid)
                    xbmc.executebuiltin("Skin.SetString(defaultset_%s,defaultset)" % settingid)

                # set the default constant value if current value is empty
                if (not curvalue and settingvalue["constantdefault"] and
                        xbmc.getCondVisibility(settingvalue["constantdefault"])):
                    skinconstants[settingid] = value

        # update skin constants if needed only
        if skinconstants:
            self.update_skin_constants(skinconstants)

    def save_skin_image(self, skinstring="", multi_image=False, header=""):
        '''let the user select an image and save it to addon_data for easy backup'''
        cur_value = xbmc.getInfoLabel("Skin.String(%s)" % skinstring).decode("utf-8")
        cur_value_org = xbmc.getInfoLabel("Skin.String(%s.org)" % skinstring).decode("utf-8")

        if not multi_image:
            # single image (allow copy to addon_data)
            value = xbmcgui.Dialog().browse(2, header, 'files', '', True, True, cur_value_org).decode("utf-8")
            if value:
                ext = value.split(".")[-1]
                newfile = (u"special://profile/addon_data/%s/custom_images/%s.%s"
                           % (xbmc.getSkinDir(), skinstring + time.strftime("%Y%m%d%H%M%S", time.gmtime()), ext))
                if "special://profile/addon_data/%s/custom_images/" % xbmc.getSkinDir() in cur_value:
                    xbmcvfs.delete(cur_value)
                xbmcvfs.copy(value, newfile)
                xbmc.executebuiltin("Skin.SetString(%s.org,%s)" % (skinstring.encode("utf-8"), value.encode("utf-8")))
                value = newfile
        else:
            # multi image
            if not cur_value_org.startswith("$"):
                delim = "\\" if "\\" in cur_value_org else "/"
                curdir = cur_value_org.rsplit(delim, 1)[0] + delim
            else:
                curdir = ""
            value = xbmcgui.Dialog().browse(0, self.addon.getLocalizedString(32005),
                                            'files', '', True, True, curdir).decode("utf-8")
        return value

    def set_skinshortcuts_property(self, setting="", window_header="", property_name=""):
        '''allows the user to make a setting for skinshortcuts using the special skinsettings dialogs'''
        cur_value = xbmc.getInfoLabel(
            "$INFO[Container(211).ListItem.Property(%s)]" %
            property_name).decode("utf-8")
        cur_value_label = xbmc.getInfoLabel(
            "$INFO[Container(211).ListItem.Property(%s.name)]" %
            property_name).decode("utf-8")
        if setting == "||IMAGE||":
            # select image
            label, value = self.select_image(setting, allow_multi=True, windowheader=windowheader)
        if setting:
            # use skin settings select dialog
            value, label = self.set_skin_setting(
                setting, window_header=window_header, sublevel="", cur_value_label=cur_value_label,
                skip_skin_string=True, cur_value=cur_value)
        else:
            # manually input string
            if not cur_value:
                cur_value = "None"
            value = xbmcgui.Dialog().input(window_header, cur_value, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
            label = value
        if label:
            from skinshortcuts import set_skinshortcuts_property
            set_skinshortcuts_property(property_name, value, label)

    def select_image(self, skinstring, allow_multi=True, windowheader="",
                     resource_addon="", skinhelper_backgrounds=False, current_value=""):
        '''helper which lets the user select an image or imagepath from resourceaddons or custom path'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        images = []
        if not windowheader:
            windowheader = self.addon.getLocalizedString(32020)
        if not current_value:
            current_value = xbmc.getInfoLabel("Skin.String(%s.label)" % skinstring).decode("utf-8")

        # none option
        images.append((self.addon.getLocalizedString(32001), "", "", "DefaultAddonNone.png"))
        # custom single
        images.append((self.addon.getLocalizedString(32004), "", "", "DefaultAddonPicture.png"))
        # custom multi
        if allow_multi:
            images.append((self.addon.getLocalizedString(32005), "", "", "DefaultFolder.png"))

        # backgrounds supplied in our special skinsettings.xml file
        skinimages = self.skinsettings
        if skinimages.get(skinstring):
            for item in skinimages[skinstring]:
                if not item["condition"] or xbmc.getCondVisibility(item["condition"]):
                    images.append((item["label"], item["value"], item["description"], item["icon"]))

        # backgrounds provided by skinhelper
        if skinhelper_backgrounds:
            from skinshortcuts import get_skinhelper_backgrounds
            for label, image in get_skinhelper_backgrounds():
                images.append((label, image, "Skin Helper Backgrounds", xbmc.getInfoLabel(image)))

        # resource addon images
        if resource_addon:
            from resourceaddons import get_resourceimages
            images += get_resourceimages(resource_addon)

        # create listitems
        listitems = []
        for label, imagepath, label2, icon in images:
            listitem = xbmcgui.ListItem(label=label, label2=label2, iconImage=icon)
            listitem.setPath(imagepath)
            listitems.append(listitem)

        # show select dialog with choices
        dialog = DialogSelect("DialogSelect.xml", "", listing=listitems, windowtitle=windowheader, richlayout=True,
                              getmorebutton=resource_addon, autofocuslabel=current_value)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        dialog.doModal()
        result = dialog.result
        del dialog
        if isinstance(result, bool):
            if result:
                # refresh listing requested by getmore button
                return self.select_image(skinstring, allow_multi, windowheader,
                                         resource_addon, skinhelper_backgrounds, current_value)
        elif result:
            label = result.getLabel().decode("utf-8")
            if label == self.addon.getLocalizedString(32004):
                # browse for single image
                custom_image = SkinSettings().save_skin_image(skinstring, False, self.addon.getLocalizedString(32004))
                if custom_image:
                    result.setPath(custom_image)
                else:
                    return self.selectimage()
            elif label == self.addon.getLocalizedString(32005):
                # browse for image path
                custom_image = SkinSettings().save_skin_image(skinstring, True, self.addon.getLocalizedString(32005))
                if custom_image:
                    result.setPath(custom_image)
                else:
                    return self.selectimage()
            # return values
            return (result.getLabel().decode("utf-8"), result.getfilename().decode("utf-8"))
        # return empty values
        return ("", "")

    @staticmethod
    def multi_select(options, window_header=""):
        '''allows the user to choose from multiple options'''
        listitems = []
        for option in options:
            if not option["condition"] or xbmc.getCondVisibility(option["condition"]):
                listitem = xbmcgui.ListItem(label=option["label"], label2=option["description"])
                listitem.setProperty("id", option["id"])
                if xbmc.getCondVisibility("Skin.HasSetting(%s)" % option["id"]) or (not xbmc.getInfoLabel(
                        "Skin.String(defaultset_%s)" % option["id"]) and xbmc.getCondVisibility(option["default"])):
                    listitem.select(selected=True)
                listitems.append(listitem)
        # show select dialog
        dialog = DialogSelect("DialogSelect.xml", "", listing=listitems, windowtitle=window_header, multiselect=True)
        dialog.doModal()
        result = dialog.result
        if result:
            for item in result:
                if item.isSelected():
                    # option is enabled
                    xbmc.executebuiltin("Skin.SetBool(%s)" % item.getProperty("id"))
                else:
                    # option is disabled
                    xbmc.executebuiltin("Skin.Reset(%s)" % item.getProperty("id"))
            # always set additional prop to define the defaults
            xbmc.executebuiltin("Skin.SetString(defaultset_%s,defaultset)" % item.getProperty("id"))
        del dialog

    def indent_xml(self, elem, level=0):
        '''helper to properly indent xml strings to file'''
        text_i = "\n" + level * "\t"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = text_i + "\t"
            if not elem.tail or not elem.tail.strip():
                elem.tail = text_i
            for elem in elem:
                self.indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = text_i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = text_i

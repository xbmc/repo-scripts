# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import ast
import os
import re
import xml.etree.ElementTree as ETree
from traceback import print_exc

import xbmc
import xbmcgui
import xbmcvfs

from . import datafunctions
from . import template
from .common import log
from .common import read_file
from .common_utils import disable_logging
from .common_utils import enable_logging
from .common_utils import offer_log_upload
from .constants import ADDON
from .constants import ADDON_NAME
from .constants import ADDON_VERSION
from .constants import HOME_WINDOW
from .constants import KODI_VERSION
from .constants import LANGUAGE
from .constants import SKIN_DIR
from .constants import SKIN_PATH
from .hash_utils import generate_file_hash
from .hash_utils import read_hashes
from .hash_utils import write_hashes
from .property_utils import has_fallback_property


class XMLFunctions:
    def __init__(self):
        self.data_func = datafunctions.DataFunctions()

        self.main_widget = {}
        self.main_background = {}
        self.main_properties = {}
        self.has_settings = False
        self.widget_count = 1

        self.loaded_property_patterns = False
        self.property_patterns = None

        self.skin_dir = SKIN_PATH

        self.check_for_shortcuts = []

    def build_menu(self, mainmenu_id, groups, num_levels, build_mode, options, minitems,
                   system_debug=False, script_debug=False):
        # Entry point for building includes.xml files
        if HOME_WINDOW.getProperty("skinshortcuts-isrunning") == "True":
            return

        HOME_WINDOW.setProperty("skinshortcuts-isrunning", "True")

        # Get a list of profiles
        profiles_xml = xbmcvfs.translatePath('special://userdata/profiles.xml')
        tree = None
        if xbmcvfs.exists(profiles_xml):
            try:
                contents = read_file(profiles_xml)
                tree = ETree.fromstring(contents)
            except FileNotFoundError:
                pass

        profilelist = []
        if tree is not None:
            profiles = tree.findall("profile")
            for profile in profiles:
                name = profile.find("name").text
                path = profile.find("directory").text
                log("Profile found: %s (%s)" % (name, path))

                # Localise the directory
                if "://" in path:
                    path = xbmcvfs.translatePath(path)

                # Base if off of the master profile
                path = xbmcvfs.translatePath(os.path.join("special://masterprofile", path))
                profilelist.append([path, "String.IsEqual(System.ProfileName,%s)" % name, name])

        else:
            name = xbmc.getInfoLabel("System.ProfileName")
            profilelist = [[xbmcvfs.translatePath("special://masterprofile/"),
                            "String.IsEqual(System.ProfileName,%s)" % name,
                            name]]

        if not self.shouldwerun(profilelist):
            log("Menu is up to date")
            HOME_WINDOW.clearProperty("skinshortcuts-isrunning")
            return

        # Create a progress dialog
        progress = xbmcgui.DialogProgressBG()
        progress.create(ADDON_NAME, LANGUAGE(32049))
        progress.update(0)

        # Write the menus
        try:
            self.writexml(profilelist, mainmenu_id, groups, num_levels, build_mode,
                          progress, options, minitems)
            complete = True
        except:
            log(print_exc())
            log("Failed to write menu")
            complete = False

        # Mark that we're no longer running, clear the progress dialog
        HOME_WINDOW.clearProperty("skinshortcuts-isrunning")
        progress.close()

        if complete:
            # Menu is built, reload the skin
            xbmc.executebuiltin("ReloadSkin()")
            return

        # Menu couldn't be built - generate a debug log
        # If we enabled debug logging
        if system_debug or script_debug:
            # Disable any logging we enabled
            disable_logging(system_debug, script_debug)
            offer_log_upload(message_id=32092)
            return

        system_debug, script_debug = enable_logging()

        if system_debug or script_debug:
            # We enabled one or more of the debug options, re-run this function
            self.build_menu(mainmenu_id, groups, num_levels, build_mode, options, minitems,
                            system_debug, script_debug)
        else:
            offer_log_upload(message_id=32092)

    @staticmethod
    def shouldwerun(profilelist):
        try:
            prop = HOME_WINDOW.getProperty("skinshortcuts-reloadmainmenu")
            HOME_WINDOW.clearProperty("skinshortcuts-reloadmainmenu")
            if prop == "True":
                log("Menu has been edited")
                return True
        except:
            pass

        # Save some settings to skin strings
        xbmc.executebuiltin("Skin.SetString(skinshortcuts-sharedmenu,%s)" %
                            (ADDON.getSetting("shared_menu")))

        # Get the skins addon.xml file
        addonpath = xbmcvfs.translatePath(os.path.join("special://skin/", 'addon.xml'))
        addon = ETree.parse(addonpath)
        extensionpoints = addon.findall("extension")
        paths = []
        skinpaths = []

        # Get the skin version
        skin_version = addon.getroot().attrib.get("version")

        # Get the directories for resolutions this skin supports
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    path = xbmcvfs.translatePath(
                        os.path.join("special://skin/", resolution.attrib.get("folder"),
                                     "script-skinshortcuts-includes.xml")
                    )
                    paths.append(path)
                    skinpaths.append(path)
                break

        # Check for the includes file
        for path in paths:
            if not xbmcvfs.exists(path):
                log("Includes file does not exist")
                return True

        hashes = read_hashes()
        if not hashes:
            log("No hashes found")
            return True

        checked_kodi_ver = False
        checked_skin_ver = False
        checked_script_ver = False
        checked_profile_list = False
        checked_pvr_vis = False
        checked_shared_menu = False
        found_full_menu = False

        for hashed in hashes:
            hashed_item = '' if not hashed else hashed[0]
            hashed_value = '' if len(hashed) < 2 else hashed[1]

            log("Comparing hashes of Item: %s Value: %s" %
                (hashed_item, hashed_value))

            if hashed_value is not None:
                if hashed_item == "::XBMCVER::":
                    # Check the skin version is still the same as hashed_value
                    checked_kodi_ver = True
                    if KODI_VERSION != hashed_value:
                        log("Now running a different version of Kodi")
                        return True

                elif hashed_item == "::SKINVER::":
                    # Check the skin version is still the same as hashed_value
                    checked_skin_ver = True
                    if skin_version != hashed_value:
                        log("Now running a different skin version")
                        return True

                elif hashed_item == "::SCRIPTVER::":
                    # Check the script version is still the same as hashed_value
                    checked_script_ver = True
                    if ADDON_VERSION != hashed_value:
                        log("Now running a different script version")
                        return True

                elif hashed_item == "::PROFILELIST::":
                    # Check the profilelist is still the same as hashed_value
                    checked_profile_list = True
                    if profilelist != hashed_value:
                        log("Profiles have changes")
                        return True

                elif hashed_item == "::HIDEPVR::":
                    checked_pvr_vis = True
                    if ADDON.getSetting("donthidepvr") != hashed_value:
                        log("PVR visibility setting has changed")

                elif hashed_item == "::SHARED::":
                    # Check whether shared-menu setting has changed
                    checked_shared_menu = True
                    if ADDON.getSetting("shared_menu") != hashed_value:
                        log("Shared menu setting has changed")
                        return True

                elif hashed_item == "::LANGUAGE::":
                    # We no longer need to rebuild on a system language change
                    pass

                elif hashed_item == "::SKINBOOL::":
                    # A boolean we need to set (if profile matches)
                    if xbmc.getCondVisibility(hashed_value[0]):
                        if hashed_value[2] == "True":
                            xbmc.executebuiltin("Skin.SetBool(%s)" % (hashed_value[1]))
                        else:
                            xbmc.executebuiltin("Skin.Reset(%s)" % (hashed_value[1]))

                elif hashed_item == "::FULLMENU::":
                    # Mark that we need to set the fullmenu bool
                    found_full_menu = True

                elif hashed_item == "::SKINDIR::":
                    # Used to import menus from one skin to another, nothing to check here
                    pass

                else:
                    try:
                        hexdigest = generate_file_hash(hashed_item)
                        if hexdigest != hashed_value:
                            log("Hash does not match for Filename: %s "
                                "Stored Hash: %s Actual Hash: %s" %
                                (hashed_item, hashed_value, hexdigest))
                            return True
                    except:
                        item = 'UNKNOWN' if not hashed_item else hashed_item
                        value = 'UNKNOWN' if hashed_value == '' else hashed_value
                        log("Failed to compare hash of Item: %s Value: %s" %
                            (item, value))

            if hashed_value is None:
                if xbmcvfs.exists(hashed_item):
                    log("New file detected %s" % hashed_item)
                    return True

        # Set or clear the FullMenu skin bool
        if found_full_menu:
            xbmc.executebuiltin("Skin.SetBool(SkinShortcuts-FullMenu)")
        else:
            xbmc.executebuiltin("Skin.Reset(SkinShortcuts-FullMenu)")

        # If the skin or script version, or profile list, haven't been checked,
        # we need to rebuild the menu (most likely we're running an old version of the script)
        if False in (checked_kodi_ver, checked_skin_ver, checked_script_ver,
                     checked_profile_list, checked_pvr_vis, checked_shared_menu):
            return True

        # If we get here, the menu does not need to be rebuilt.
        return False

    # noinspection PyListCreation
    def writexml(self, profilelist, mainmenu_id, groups, num_levels, build_mode,
                 progress, options, minitems):
        # Reset the hashlist, add the profile list and script version
        hashlist = []
        hashlist.append(["::PROFILELIST::", profilelist])
        hashlist.append(["::SCRIPTVER::", ADDON_VERSION])
        hashlist.append(["::XBMCVER::", KODI_VERSION])
        hashlist.append(["::HIDEPVR::", ADDON.getSetting("donthidepvr")])
        hashlist.append(["::SHARED::", ADDON.getSetting("shared_menu")])
        hashlist.append(["::SKINDIR::", SKIN_DIR])

        # Clear any skin settings for backgrounds and widgets
        self.data_func.reset_backgroundandwidgets()
        self.widget_count = 1

        # Create a new tree and includes for the various groups
        tree = ETree.ElementTree(ETree.Element("includes"))
        root = tree.getroot()

        # Create a Template object and pass it the root
        temple_object = template.Template()
        temple_object.includes = root
        temple_object.progress = progress

        # Get any shortcuts we're checking for
        self.check_for_shortcuts = []
        overridestree = self.data_func.get_overrides_skin()
        check_for_shortcuts_overrides = overridestree.getroot().findall("checkforshortcut")
        for check_for_shortcut_override in check_for_shortcuts_overrides:
            if "property" not in check_for_shortcut_override.attrib:
                continue

            # Add this to the list of shortcuts we'll check for
            self.check_for_shortcuts.append(
                (check_for_shortcut_override.text.lower(),
                 check_for_shortcut_override.attrib.get("property"),
                 "False")
            )

        mainmenu_tree = ETree.SubElement(root, "include")
        mainmenu_tree.set("name", "skinshortcuts-mainmenu")

        submenu_trees = []
        for level in range(0, int(num_levels) + 1):
            _ = ETree.SubElement(root, "include")
            subtree = ETree.SubElement(root, "include")
            if level == 0:
                subtree.set("name", "skinshortcuts-submenu")
            else:
                subtree.set("name", "skinshortcuts-submenu-%s" % str(level))

            if subtree not in submenu_trees:
                submenu_trees.append(subtree)

        allmenu_tree = []
        if build_mode == "single":
            allmenu_tree = ETree.SubElement(root, "include")
            allmenu_tree.set("name", "skinshortcuts-allmenus")

        profile_percent = 100 / len(profilelist)
        profile_count = -1

        submenu_nodes = {}

        for profile in profilelist:
            log("Building menu for profile %s" % (profile[2]))
            # Load profile details
            profile_count += 1

            # Reset whether we have settings
            self.has_settings = False

            # Reset any checkForShortcuts to say we haven't found them
            new_check_for_shortcuts = []
            for check_for_shortcut in self.check_for_shortcuts:
                new_check_for_shortcuts.append(
                    (check_for_shortcut[0], check_for_shortcut[1], "False")
                )

            self.check_for_shortcuts = new_check_for_shortcuts

            # Clear any previous labelID's
            self.data_func.clear_label_id()

            # Clear any additional properties, which may be for a different profile
            self.data_func.current_properties = None

            # Create objects to hold the items
            menuitems = []
            submenu_items = []
            template_main_menu_items = ETree.Element("includes")

            # If building the main menu, split the mainmenu shortcut nodes into the menuitems list
            full_menu = False
            if groups == "" or groups.split("|", maxsplit=1)[0] == "mainmenu":
                # Set a skinstring that marks that we're providing the whole menu
                xbmc.executebuiltin("Skin.SetBool(SkinShortcuts-FullMenu)")
                hashlist.append(["::FULLMENU::", "True"])
                for node in self.data_func.get_shortcuts("mainmenu", profile_dir=profile[0]) \
                        .findall("shortcut"):
                    menuitems.append(node)
                    submenu_items.append(node)

                full_menu = True

            else:
                # Clear any skinstring marking that we're providing the whole menu
                xbmc.executebuiltin("Skin.Reset(SkinShortcuts-FullMenu)")
                hashlist.append(["::FULLMENU::", "False"])

            # If building specific groups, split them into the menuitems list
            if groups != "":
                for group in groups.split("|"):
                    if group != "mainmenu":
                        menuitems.append(group)

            if len(menuitems) == 0:
                # No groups to build
                break

            itemidmainmenu = 0
            ratio_denominator = float(len(menuitems))
            if len(temple_object.other_templates) > 0:
                ratio_denominator = ratio_denominator * 2.0

            percent = float(profile_percent) / ratio_denominator

            temple_object.percent = percent * (len(menuitems))

            for index, item in enumerate(menuitems):
                itemidmainmenu += 1
                current_progress = (profile_percent * profile_count) + (percent * (index + 1))
                progress.update(int(current_progress))
                temple_object.current = current_progress
                submenu_default_id = None
                template_current_main_menu_item = None

                if not isinstance(item, str):
                    # This is a main menu item (we know this because it's an element, not a string)
                    submenu = item.find("labelID").text

                    # Build the menu item
                    menuitem, all_props = self.build_element(
                        item,
                        "mainmenu",
                        None,
                        profile[1], self.data_func.slugify(submenu, convert_int=True),
                        itemid=itemidmainmenu,
                        options=options
                    )

                    # Save a copy for the template
                    template_main_menu_items.append(temple_object.copy_tree(menuitem))
                    template_current_main_menu_item = temple_object.copy_tree(menuitem)

                    # Get submenu defaultID
                    submenu_default_id = item.find("defaultID").text

                    # Remove any template-only properties
                    other_properties, _, template_only = self.data_func.get_property_requires()
                    for key in other_properties:
                        if key in all_props and key in template_only:  # pylint: disable=unsupported-membership-test
                            # This key is template-only
                            menuitem.remove(all_props[key])
                            all_props.pop(key)

                    # Add the menu item to the various includes, retaining a reference to them
                    mainmenu_item_a = temple_object.copy_tree(menuitem)
                    mainmenu_tree.append(mainmenu_item_a)

                    mainmenu_item_b = None
                    if build_mode == "single":
                        mainmenu_item_b = temple_object.copy_tree(menuitem)
                        allmenu_tree.append(mainmenu_item_b)

                else:
                    # It's an additional menu, so get its labelID
                    submenu = self.data_func.get_label_id(item, None)

                    # And clear mainmenu_item_a and mainmenu_item_b, so we don't
                    # incorrectly add properties to an actual main menu item
                    mainmenu_item_a = None
                    mainmenu_item_b = None

                # Build the submenu
                for count, submenu_tree in enumerate(submenu_trees):
                    submenu_visibility_name = submenu
                    if count == 1:
                        submenu = "%s.%s" % (submenu, str(count))
                    elif count != 0:
                        submenu = submenu[:-1] + str(count)
                        submenu_visibility_name = submenu[:-2]

                    justmenu_tree_a = []
                    justmenu_tree_b = []
                    # Get the tree's we're going to write the menu to
                    if "noGroups" not in options:
                        if submenu in submenu_nodes:
                            justmenu_tree_a = submenu_nodes[submenu][0]
                            justmenu_tree_b = submenu_nodes[submenu][1]
                        else:
                            # Create these nodes
                            justmenu_tree_a = ETree.SubElement(root, "include")
                            justmenu_tree_b = ETree.SubElement(root, "include")

                            if count != 0:
                                group_include = \
                                    "%s-%s" % \
                                    (self.data_func.slugify(submenu[:-2], convert_int=True),
                                     submenu[-1:])
                            else:
                                group_include = self.data_func.slugify(submenu, convert_int=True)

                            justmenu_tree_a.set("name",
                                                "skinshortcuts-group-%s" % group_include)
                            justmenu_tree_b.set("name",
                                                "skinshortcuts-group-alt-%s" % group_include)

                            submenu_nodes[submenu] = [justmenu_tree_a, justmenu_tree_b]

                    itemidsubmenu = 0

                    # Get the shortcuts for the submenu
                    if count == 0:
                        submenudata = self.data_func.get_shortcuts(submenu, submenu_default_id,
                                                                   profile[0])
                    else:
                        submenudata = self.data_func.get_shortcuts(submenu, None,
                                                                   profile[0], is_sub_level=True)

                    if isinstance(submenudata, list):
                        submenuitems = submenudata
                    else:
                        submenuitems = submenudata.findall("shortcut")

                    # Are there any submenu items for the main menu?
                    if count == 0:
                        if len(submenuitems) != 0:
                            try:
                                has_submenu = ETree.SubElement(mainmenu_item_a, "property")
                                has_submenu.set("name", "hasSubmenu")
                                has_submenu.text = "True"
                                if build_mode == "single":
                                    has_submenu = ETree.SubElement(mainmenu_item_b, "property")
                                    has_submenu.set("name", "hasSubmenu")
                                    has_submenu.text = "True"
                            except:
                                # There probably isn't a main menu
                                pass

                        else:
                            try:
                                has_submenu = ETree.SubElement(mainmenu_item_a, "property")
                                has_submenu.set("name", "hasSubmenu")
                                has_submenu.text = "False"
                                if build_mode == "single":
                                    has_submenu = ETree.SubElement(mainmenu_item_b, "property")
                                    has_submenu.set("name", "hasSubmenu")
                                    has_submenu.text = "False"
                            except:
                                # There probably isn't a main menu
                                pass

                    # If we're building a single menu, update the onclicks of the main menu
                    if build_mode == "single" and not len(submenuitems) == 0 and \
                            not isinstance(item, str):
                        setprop_str = "SetProperty(submenuVisibility,%s,10000)" % \
                                      self.data_func.slugify(submenu_visibility_name,
                                                             convert_int=True)

                        for onclickelement in mainmenu_item_b.findall("onclick"):
                            if "condition" in onclickelement.attrib:
                                onclickelement.set(
                                    "condition",
                                    "String.IsEqual(Window(10000)"
                                    ".Property(submenuVisibility),%s) + [%s]" %
                                    (self.data_func.slugify(submenu_visibility_name,
                                                            convert_int=True),
                                     onclickelement.attrib.get("condition"))
                                )
                                newonclick = ETree.SubElement(mainmenu_item_b, "onclick")
                                newonclick.text = setprop_str
                                newonclick.set("condition", onclickelement.attrib.get("condition"))

                            else:
                                onclickelement.set(
                                    "condition",
                                    "String.IsEqual(Window(10000).Property(submenuVisibility),%s)"
                                    % (self.data_func.slugify(submenu_visibility_name,
                                                              convert_int=True))
                                )
                                newonclick = ETree.SubElement(mainmenu_item_b, "onclick")
                                newonclick.text = setprop_str

                    # Build the submenu items
                    template_submenu_items = ETree.Element("includes")
                    for submenu_item in submenuitems:
                        itemidsubmenu += 1
                        # Build the item without any visibility conditions
                        menuitem, all_props = self.build_element(submenu_item, submenu, None,
                                                                 profile[1], itemid=itemidsubmenu,
                                                                 mainmenuid=itemidmainmenu,
                                                                 options=options)
                        is_submenu_element = ETree.SubElement(menuitem, "property")
                        is_submenu_element.set("name", "isSubmenu")
                        is_submenu_element.text = "True"

                        # Save a copy for the template
                        template_submenu_items.append(temple_object.copy_tree(menuitem))

                        # Remove any template-only properties
                        other_properties, _, template_only = self.data_func.get_property_requires()

                        for key in other_properties:
                            # pylint: disable=unsupported-membership-test,useless-suppression
                            if key in all_props and key in template_only:
                                # This key is template-only
                                menuitem.remove(all_props[key])
                                all_props.pop(key)

                        menu_item_copy = temple_object.copy_tree(menuitem)

                        if "noGroups" not in options:
                            # Add it, with appropriate visibility conditions,
                            # to the various submenu includes
                            justmenu_tree_a.append(menuitem)

                            visibility_element = menu_item_copy.find("visible")
                            visibility_element.text = \
                                "[%s] + %s" % (
                                    visibility_element.text,
                                    "String.IsEqual(Window(10000).Property(submenuVisibility),%s)" %
                                    (self.data_func.slugify(submenu_visibility_name,
                                                            convert_int=True))
                                )

                            justmenu_tree_b.append(menu_item_copy)

                        if build_mode == "single" and not isinstance(item, str):
                            # Add the property 'submenuVisibility'
                            allmenu_tree_copy = temple_object.copy_tree(menu_item_copy)
                            submenu_visibility = ETree.SubElement(allmenu_tree_copy, "property")
                            submenu_visibility.set("name", "submenuVisibility")
                            submenu_visibility.text = \
                                self.data_func.slugify(submenu_visibility_name, convert_int=True)
                            allmenu_tree.append(allmenu_tree_copy)

                        menu_item_copy = temple_object.copy_tree(menuitem)
                        visibility_element = menu_item_copy.find("visible")
                        visibility_element.text = \
                            "[%s] + %s" % (
                                visibility_element.text,
                                "String.IsEqual(Container(%s)"
                                ".ListItem.Property(submenuVisibility),%s)" %
                                (mainmenu_id,
                                 self.data_func.slugify(submenu_visibility_name,
                                                        convert_int=True))
                            )
                        submenu_tree.append(menu_item_copy)
                    if len(submenuitems) == 0 and "noGroups" not in options:
                        # There aren't any submenu items, so add a 'description'
                        # element to the group includes
                        # so that Kodi doesn't think they're invalid
                        newelement = ETree.Element("description")
                        newelement.text = "No items"
                        justmenu_tree_a.append(newelement)
                        justmenu_tree_b.append(newelement)

                    # Build the template for the submenu
                    build_others = False
                    if item in submenu_items:
                        build_others = True

                    temple_object.parse_items(
                        "submenu", count, template_submenu_items, profile[2],
                        profile[1], "String.IsEqual(Container(%s).ListItem"
                                    ".Property(submenuVisibility),%s)" %
                                    (mainmenu_id,
                                     self.data_func.slugify(submenu_visibility_name,
                                                            convert_int=True)),
                        item, None, build_others, mainmenuitems=template_current_main_menu_item)

            if self.has_settings is False:
                # Check if the overrides asks for a forced settings...
                overridestree = self.data_func.get_overrides_skin()
                force_settings = overridestree.getroot().find("forcesettings")
                if force_settings is not None:
                    # We want a settings option to be added
                    newelement = ETree.SubElement(mainmenu_tree, "item")
                    ETree.SubElement(newelement, "label").text = "$LOCALIZE[10004]"
                    ETree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
                    ETree.SubElement(newelement, "onclick").text = "ActivateWindow(settings)"
                    ETree.SubElement(newelement, "visible").text = profile[1]

                    if build_mode == "single":
                        newelement = ETree.SubElement(mainmenu_tree, "item")
                        ETree.SubElement(newelement, "label").text = "$LOCALIZE[10004]"
                        ETree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
                        ETree.SubElement(newelement, "onclick").text = "ActivateWindow(settings)"
                        ETree.SubElement(newelement, "visible").text = profile[1]

            # Add a value to the variable for all checkForShortcuts
            for check_for_shortcut in self.check_for_shortcuts:
                if profile[1] is not None and xbmc.getCondVisibility(profile[1]):
                    # Current profile - set the skin bool
                    if check_for_shortcut[2] == "True":
                        xbmc.executebuiltin("Skin.SetBool(%s)" % (check_for_shortcut[1]))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % (check_for_shortcut[1]))

                # Save this to the hashes file, so we can set it on profile changes
                hashlist.append(["::SKINBOOL::", [profile[1], check_for_shortcut[1],
                                                  check_for_shortcut[2]]])

            # Build the template for the main menu
            temple_object.parse_items("mainmenu", 0, template_main_menu_items, profile[2],
                                      profile[1], "", "", mainmenu_id, True)

            # If we haven't built enough main menu items, copy the ones we have
            while itemidmainmenu < minitems and full_menu and len(mainmenu_tree) != 0:
                updated_menu_tree = temple_object.copy_tree(mainmenu_tree)
                for item in updated_menu_tree:
                    itemidmainmenu += 1
                    # Update ID
                    item.set("id", str(itemidmainmenu))
                    for id_element in item.findall("property"):
                        if id_element.attrib.get("name") == "id":
                            id_element.text = "$NUM[%s]" % (str(itemidmainmenu))

                    mainmenu_tree.append(item)

        # Build any 'Other' templates
        temple_object.write_others()

        progress.update(100, message=LANGUAGE(32098))

        # Get the skins addon.xml file
        addon_xml = xbmcvfs.translatePath(os.path.join("special://skin/", 'addon.xml'))
        addon = ETree.parse(addon_xml)
        extensionpoints = addon.findall("extension")

        skin_version = addon.getroot().attrib.get("version")
        # Append the skin version to the hashlist
        hashlist.append(["::SKINVER::", skin_version])

        # indent the tree
        self.data_func.indent(tree.getroot())

        # create a set of hashable files
        hashable = set()
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get("point") == "xbmc.gui.skin":
                resolutions = extensionpoint.findall("res")
                for resolution in resolutions:
                    path = xbmcvfs.translatePath(
                        os.path.join(self.skin_dir, resolution.attrib.get("folder"),
                                     "script-skinshortcuts-includes.xml")
                    )
                    tree.write(path, encoding="UTF-8")  # writing includes
                    hashable.add(path)

        hashable.update(self.data_func.hashable)
        hashable.update(temple_object.hashable)

        for item in hashable:  # generate a hash for all paths
            hexdigest = generate_file_hash(item)
            if hexdigest:
                hashlist.append([item, hexdigest])

        # Save the hashes
        write_hashes(hashlist)

    def build_element(self, item, group_name, visibility_condition, profile_visibility,
                      submenu_visibility=None, itemid=-1, mainmenuid=None, options=None):
        # This function will build an element for the passed Item in

        if options is None:
            options = []

        # Create the element
        newelement = ETree.Element("item")
        all_props = {}

        # Set ID
        if itemid != -1:
            newelement.set("id", str(itemid))

        idproperty = ETree.SubElement(newelement, "property")
        idproperty.set("name", "id")
        idproperty.text = "$NUMBER[%s]" % (str(itemid))
        all_props["id"] = idproperty

        # Set main menu id
        if mainmenuid:
            mainmenuidproperty = ETree.SubElement(newelement, "property")
            mainmenuidproperty.set("name", "mainmenuid")
            mainmenuidproperty.text = "%s" % (str(mainmenuid))
            all_props[mainmenuid] = mainmenuidproperty

        # Label and label2
        ETree.SubElement(newelement, "label").text = \
            self.data_func.local(item.find("label").text)[1]
        ETree.SubElement(newelement, "label2").text = \
            self.data_func.local(item.find("label2").text)[1]

        # Icon and thumb
        icon = item.find("override-icon")
        if icon is None:
            icon = item.find("icon")

        if icon is None:
            ETree.SubElement(newelement, "icon").text = "DefaultShortcut.png"
        else:
            ETree.SubElement(newelement, "icon").text = icon.text

        thumb = item.find("thumb")
        if thumb is not None:
            ETree.SubElement(newelement, "thumb").text = item.find("thumb").text

        # labelID and defaultID
        label_id = ETree.SubElement(newelement, "property")
        label_id.text = item.find("labelID").text
        label_id.set("name", "labelID")
        all_props["labelID"] = label_id

        default_id = ETree.SubElement(newelement, "property")
        default_id.text = item.find("defaultID").text
        default_id.set("name", "defaultID")
        all_props["defaultID"] = default_id

        # Check if the item is disabled
        if item.find("disabled") is not None:
            # It is, so we set it to be invisible, add an empty onclick and return
            ETree.SubElement(newelement, "visible").text = "False"
            ETree.SubElement(newelement, "onclick").text = "noop"
            return newelement, all_props

        # Clear cloned options if main menu
        if group_name == "mainmenu":
            self.main_widget = {}
            self.main_background = {}
            self.main_properties = {}

        # Additional properties
        properties = ast.literal_eval(item.find("additional-properties").text)
        for prop in properties:
            if prop[0] == "node.visible":
                visible_property = ETree.SubElement(newelement, "visible")
                visible_property.text = prop[1]
            else:
                additionalproperty = ETree.SubElement(newelement, "property")
                additionalproperty.set("name", prop[0])
                additionalproperty.text = prop[1]
                all_props[prop[0]] = additionalproperty

                # If this is a widget or background, set a skin setting to say it's enabled
                if prop[0] == "widget":
                    xbmc.executebuiltin("Skin.SetBool(skinshortcuts-widget-%s)" % prop[1])
                    # And if it's the main menu, list it
                    if group_name == "mainmenu":
                        xbmc.executebuiltin("Skin.SetString(skinshortcuts-widget-%s,%s)" %
                                            (str(self.widget_count), prop[1]))
                        self.widget_count += 1

                elif prop[0] == "background":
                    xbmc.executebuiltin("Skin.SetBool(skinshortcuts-background-%s)" % prop[1])

                # If this is the main menu, and we're cloning widgets,
                # backgrounds or properties...
                if group_name == "mainmenu":
                    if "clonewidgets" in options:
                        widget_properties = ["widget", "widgetName", "widgetType",
                                             "widgetTarget", "widgetPath", "widgetPlaylist"]
                        if prop[0] in widget_properties:
                            self.main_widget[prop[0]] = prop[1]

                    if "clonebackgrounds" in options:
                        background_properties = ["background", "backgroundName",
                                                 "backgroundPlaylist", "backgroundPlaylistName"]
                        if prop[0] in background_properties:
                            self.main_background[prop[0]] = prop[1]

                    if "cloneproperties" in options:
                        self.main_properties[prop[0]] = prop[1]

                # For backwards compatibility, save widgetPlaylist as widgetPath too
                if prop[0] == "widgetPlaylist":
                    additionalproperty = ETree.SubElement(newelement, "property")
                    additionalproperty.set("name", "widgetPath")
                    additionalproperty.text = prop[1]

        # Get fallback properties, property requirements, template_only value of properties
        fallback_properties, fallbacks = self.data_func.get_custom_property_fallbacks(group_name)

        # Add fallback properties
        source_properties = dict(properties)
        for key in fallback_properties:
            if key not in all_props:
                # Check whether we have a fallback for the value
                for property_match in fallbacks[key]:
                    if has_fallback_property(property_match, source_properties):
                        additionalproperty = ETree.SubElement(newelement, "property")
                        additionalproperty.set("name", key)
                        additionalproperty.text = property_match[0]
                        all_props[key] = additionalproperty
                        break

        # Get property requirements
        other_properties, requires, _ = self.data_func.get_property_requires()

        # Remove any properties whose requirements haven't been met
        for key in other_properties:
            # pylint: disable=unsubscriptable-object,unsupported-membership-test
            if key in all_props and key in requires and requires[key] not in all_props:
                # This properties requirements aren't met
                newelement.remove(all_props[key])
                all_props.pop(key)

        # Primary visibility
        visibility = item.find("visibility")
        if visibility is not None:
            ETree.SubElement(newelement, "visible").text = visibility.text

        # additional onclick (group overrides)
        onclicks = item.findall("additional-action")
        for onclick in onclicks:
            onclickelement = ETree.SubElement(newelement, "onclick")
            onclickelement.text = onclick.text
            if "condition" in onclick.attrib:
                onclickelement.set("condition", onclick.attrib.get("condition"))

        # Onclick
        onclicks = item.findall("override-action")
        if len(onclicks) == 0:
            onclicks = item.findall("action")

        for onclick in onclicks:
            onclickelement = ETree.SubElement(newelement, "onclick")

            # Upgrade action if necessary
            onclick.text = self.data_func.upgrade_action(onclick.text)

            # PVR Action
            if onclick.text.startswith("pvr-channel://"):
                # PVR action
                onclickelement.text = \
                    "RunScript(script.skinshortcuts,type=launchpvr&channel=%s)" % \
                    onclick.text.replace("pvr-channel://", "")

            elif onclick.text.startswith("ActivateWindow(") and SKIN_PATH in onclick.text:
                # Skin-relative links
                try:
                    action_parts = onclick.text[15:-1].split(",")
                    action_parts[1] = action_parts[1].replace(SKIN_PATH, "")
                    _ = action_parts[1].split(os.sep)
                    new_action = "special://skin"
                    for action_part in action_parts[1].split(os.sep):
                        if action_part != "":
                            new_action = "%s/%s" % (new_action, action_part)
                    if len(action_parts) == 2:
                        onclickelement.text = "ActivateWindow(%s,%s)" % \
                                              (action_parts[0], new_action)
                    else:
                        onclickelement.text = "ActivateWindow(%s,%s,%s)" % \
                                              (action_parts[0], new_action, action_parts[2])
                except:
                    pass

            else:
                onclickelement.text = onclick.text

            # Also add it as a path property
            if not self.property_exists("path", newelement) and "path" not in all_props:
                # we only add the path property if there isn't already one in the list
                # because it has to be unique in Kodi lists
                pathelement = ETree.SubElement(newelement, "property")
                pathelement.set("name", "path")
                pathelement.text = onclickelement.text
                all_props["path"] = pathelement

            # Get 'list' property (the action property of an ActivateWindow shortcut)
            if not self.property_exists("list", newelement) and "list" not in all_props:
                # we only add the list property if there isn't already one in the list
                # because it has to be unique in Kodi lists
                list_element = ETree.SubElement(newelement, "property")
                list_element.set("name", "list")
                list_element.text = \
                    self.data_func.get_list_property(onclickelement.text.replace('"', ''))
                all_props["list"] = list_element

            if onclick.text == "ActivateWindow(Settings)":
                self.has_settings = True

            if "condition" in onclick.attrib:
                onclickelement.set("condition", onclick.attrib.get("condition"))

            if len(self.check_for_shortcuts) != 0:
                # Check if we've been asked to watch for this shortcut
                new_check_for_shortcuts = []
                for check_for_shortcut in self.check_for_shortcuts:
                    if onclick.text.lower() == check_for_shortcut[0]:
                        # They match, change the value to True
                        new_check_for_shortcuts.append((check_for_shortcut[0],
                                                        check_for_shortcut[1], "True"))
                    else:
                        new_check_for_shortcuts.append(check_for_shortcut)

                self.check_for_shortcuts = new_check_for_shortcuts

        # Visibility
        if visibility_condition is not None:
            visibility_element = ETree.SubElement(newelement, "visible")
            if profile_visibility is not None:
                visibility_element.text = "%s + [%s]" % (profile_visibility, visibility_condition)
            else:
                visibility_element.text = visibility_condition

            is_submenu_element = ETree.SubElement(newelement, "property")
            is_submenu_element.set("name", "isSubmenu")
            is_submenu_element.text = "True"
            all_props["isSubmenu"] = is_submenu_element

        elif profile_visibility is not None:
            visibility_element = ETree.SubElement(newelement, "visible")
            visibility_element.text = profile_visibility

        # Submenu visibility
        if submenu_visibility is not None:
            submenu_visibility_element = ETree.SubElement(newelement, "property")
            submenu_visibility_element.set("name", "submenuVisibility")
            if submenu_visibility.isdigit():
                submenu_visibility_element.text = "$NUMBER[%s]" % submenu_visibility
            else:
                submenu_visibility_element.text = self.data_func.slugify(submenu_visibility)

        # Group name
        group = ETree.SubElement(newelement, "property")
        group.set("name", "group")
        group.text = group_name
        all_props["group"] = group

        # If this isn't the main menu, and we're cloning widgets or backgrounds...
        if group_name != "mainmenu":
            if "clonewidgets" in options and len(list(self.main_widget.keys())) != 0:
                for key in list(self.main_widget.keys()):
                    additionalproperty = ETree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.main_widget[key]
                    all_props[key] = additionalproperty

            if "clonebackgrounds" in options and len(list(self.main_background.keys())) != 0:
                for key in list(self.main_background.keys()):
                    additionalproperty = ETree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.data_func.local(self.main_background[key])[1]
                    all_props[key] = additionalproperty

            if "cloneproperties" in options and len(list(self.main_properties.keys())) != 0:
                for key in list(self.main_properties.keys()):
                    additionalproperty = ETree.SubElement(newelement, "property")
                    additionalproperty.set("name", key)
                    additionalproperty.text = self.data_func.local(self.main_properties[key])[1]
                    all_props[key] = additionalproperty

        property_patterns = self.get_property_patterns(label_id.text, group_name)
        if len(property_patterns) > 0:
            property_replacements = self.get_property_replacements(newelement)
            for property_name in list(property_patterns.keys()):
                property_pattern = property_patterns[property_name][0]
                for original, replacement in property_replacements:
                    regexp_pattern = re.compile(re.escape(original), re.IGNORECASE)
                    property_pattern = regexp_pattern.sub(replacement.replace("\\", r"\\"),
                                                          property_pattern)

                additionalproperty = ETree.SubElement(newelement, "property")
                additionalproperty.set("name", property_name)
                additionalproperty.text = property_pattern
                all_props[property_name] = additionalproperty

        return newelement, all_props

    def get_property_patterns(self, label_id, group):
        property_patterns = {}
        if not self.loaded_property_patterns:
            overrides = self.data_func.get_overrides_skin()
            self.property_patterns = overrides.getroot().findall("propertypattern")
            self.loaded_property_patterns = True

        for property_pattern_element in self.property_patterns:
            property_name = property_pattern_element.get("property")
            property_group = property_pattern_element.get("group")

            if not property_name or not property_group or property_group != group or \
                    not property_pattern_element.text:
                continue

            property_label_id = property_pattern_element.get("labelID")
            if not property_label_id:
                if property_name not in property_patterns:
                    property_patterns[property_name] = [property_pattern_element.text, False]

            elif property_label_id == label_id:
                if property_name not in property_patterns or \
                        property_patterns[property_name][1] is False:
                    property_patterns[property_name] = [property_pattern_element.text, True]

        return property_patterns

    @staticmethod
    def get_property_replacements(element):
        property_replacements = []
        for sub_element in list(element):
            if sub_element.tag == "property":
                property_name = sub_element.get("name")
                if property_name and sub_element.text:
                    property_replacements.append(("::%s::" % property_name, sub_element.text))

            elif sub_element.text:
                property_replacements.append(("::%s::" % sub_element.tag, sub_element.text))

        return property_replacements

    @staticmethod
    def property_exists(property_name, element):
        for item in element.findall("property"):
            if property_name in item.attrib:
                return True

        return False

    @staticmethod
    def find_include_position(source_list, item):
        try:
            return source_list.index(item)
        except:
            return None

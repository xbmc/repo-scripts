# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import _thread as thread
import ast
import calendar
import random
import xml.etree.ElementTree as ETree
from time import gmtime
from traceback import print_exc

import xbmc
import xbmcgui
import xbmcvfs

from . import datafunctions
from . import library
from .common import log
from .common_utils import ShowDialog
from .common_utils import disable_logging
from .common_utils import enable_logging
from .common_utils import offer_log_upload
from .constants import CWD
from .constants import DATA_PATH
from .constants import DEFAULT_PATH
from .constants import HOME_WINDOW
from .constants import LANGUAGE
from .constants import SKIN_DIR
from .constants import SKIN_PATH
from .constants import SKIN_SHORTCUTS_PATH
from .property_utils import has_fallback_property
from .property_utils import read_properties
from .property_utils import write_properties

ACTION_CANCEL_DIALOG = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)
ACTION_CONTEXT_MENU = (117,)

if not xbmcvfs.exists(DATA_PATH):
    xbmcvfs.mkdir(DATA_PATH)


def is_hebrew(text):
    for _chr in text:
        if 1488 <= ord(_chr) <= 1514:
            return True
    return False


class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args)

        self.data_func = datafunctions.DataFunctions()
        self.lib_func = library.LibraryFunctions()

        self.group = kwargs["group"]
        try:
            self.default_group = kwargs["default_group"]
            if self.default_group == "":
                self.default_group = None
        except:
            self.default_group = None
        self.nolabels = kwargs["nolabels"]
        self.groupname = kwargs["groupname"]
        self.shortcutgroup = 1

        # Empty arrays for different shortcut types
        self.thumbnail_browse_default = None
        self.thumbnail_none = None
        self.background_browse = None
        self.background_browse_default = None
        self.widget_playlists = False
        self.widget_playlists_type = None
        self.widget_rename = True

        # Variables for overrides
        self.on_back = {}
        self.save_with_property = []

        # Has skin overridden GUI 308
        self.always_reset = False
        self.always_restore = False

        self.all_list_items = []

        # Additional button ID's we'll handle for setting custom properties
        self.custom_property_buttons = {}
        self.custom_toggle_buttons = {}

        # Context menu
        self.context_controls = []
        self.context_items = []

        # Onclicks
        self.custom_on_click = {}

        self.window_properties = {}

        self.change_made = False

        self.window_id = None
        self.current_window = None
        self.current_dict = {}
        self.past_dict = {}
        self.backgrounds = []
        self.thumbnails = []

        log('Management module loaded')

    def onInit(self):  # pylint: disable=invalid-name
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            self.current_window = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            xbmcgui.Window(self.window_id).setProperty('groupname', self.group)
            if self.groupname is not None:
                xbmcgui.Window(self.window_id).setProperty('groupDisplayName', self.groupname)

            # Load widget and background names
            self._load_overrides()

            # Load context menu options
            self._load_overrides_context()

            # Load additional onclick overrides
            self._load_overrides_onclick()

            # Load additional button ID's we'll handle for custom properties
            self._load_custom_property_buttons()

            # Load current shortcuts
            self.load_shortcuts()

            # Set window title label
            try:
                if self.getControl(500).getLabel() == "":
                    if self.group == "mainmenu":
                        self.getControl(500).setLabel(LANGUAGE(32071))
                    elif self.groupname is not None:
                        self.getControl(500).setLabel(LANGUAGE(32080) % self.groupname)
                    else:
                        self.getControl(500).setLabel(LANGUAGE(32072))
            except:
                pass

            # Set enabled condition for various controls
            has111 = True
            try:
                self.getControl(111).setEnableCondition(
                    "String.IsEmpty(Container(211).ListItem.Property(LOCKED))"
                )
            except:
                has111 = False
            try:
                self.getControl(302).setEnableCondition(
                    "String.IsEmpty(Container(211).ListItem.Property(LOCKED))"
                )
            except:
                pass
            try:
                self.getControl(307).setEnableCondition(
                    "String.IsEmpty(Container(211).ListItem.Property(LOCKED))"
                )
            except:
                pass
            try:
                self.getControl(401).setEnableCondition(
                    "String.IsEmpty(Container(211).ListItem.Property(LOCKED))"
                )
            except:
                pass

            # Set button labels
            if self.nolabels == "false":
                try:
                    if self.getControl(301).getLabel() == "":
                        self.getControl(301).setLabel(LANGUAGE(32000))
                except:
                    log("No add shortcut button on GUI (id 301)")
                try:
                    if self.getControl(302).getLabel() == "":
                        self.getControl(302).setLabel(LANGUAGE(32001))
                except:
                    log("No delete shortcut button on GUI (id 302)")
                try:
                    if self.getControl(303).getLabel() == "":
                        self.getControl(303).setLabel(LANGUAGE(32002))
                except:
                    log("No move shortcut up button on GUI (id 303)")
                try:
                    if self.getControl(304).getLabel() == "":
                        self.getControl(304).setLabel(LANGUAGE(32003))
                except:
                    log("No move shortcut down button on GUI (id 304)")

                try:
                    if self.getControl(305).getLabel() == "":
                        self.getControl(305).setLabel(LANGUAGE(32025))
                except:
                    log("Not set label button on GUI (id 305)")

                try:
                    if self.getControl(306).getLabel() == "":
                        self.getControl(306).setLabel(LANGUAGE(32026))
                except:
                    log("No edit thumbnail button on GUI (id 306)")

                try:
                    if self.getControl(307).getLabel() == "":
                        self.getControl(307).setLabel(LANGUAGE(32027))
                except:
                    log("Not edit action button on GUI (id 307)")

                try:
                    if self.getControl(308).getLabel() == "":
                        self.getControl(308).setLabel(LANGUAGE(32028))
                except:
                    log("No reset shortcuts button on GUI (id 308)")

                try:
                    if self.getControl(309).getLabel() == "":
                        self.getControl(309).setLabel(LANGUAGE(32044))
                    log("Warning: Deprecated widget button (id 309)")
                except:
                    pass
                try:
                    if self.getControl(310).getLabel() == "":
                        self.getControl(310).setLabel(LANGUAGE(32045))
                except:
                    log("No background button on GUI (id 310)")
                try:
                    if self.getControl(312).getLabel() == "":
                        self.getControl(312).setLabel(LANGUAGE(32044))
                except:
                    log("No widget button on GUI (id 309)")

                try:
                    if self.getControl(401).getLabel() == "":
                        self.getControl(401).setLabel(LANGUAGE(32048))
                except:
                    log("No widget button on GUI (id 401)")

            # Load library shortcuts in thread
            thread.start_new_thread(self.lib_func.load_all_library, ())

            if has111:
                try:
                    self._display_shortcuts()
                except:
                    pass

            # Clear window property indicating we're loading
            HOME_WINDOW.clearProperty("skinshortcuts-loading")

    # ======================
    # === LOAD/SAVE DATA ===
    # ======================

    def load_shortcuts(self, include_user_shortcuts=True):
        log("Loading shortcuts")
        self.data_func.clear_label_id()

        is_sub_level = False
        if "." in self.group and self.group.rsplit(".", 1)[1].isdigit() and \
                int(self.group.rsplit(".", 1)[1]) in range(1, 6):
            is_sub_level = True

        if include_user_shortcuts:
            shortcuts = self.data_func.get_shortcuts(self.group, default_group=self.default_group,
                                                     is_sub_level=is_sub_level)
        else:
            shortcuts = self.data_func.get_shortcuts(self.group, default_group=self.default_group,
                                                     defaults_only=True)

        # listitems = []
        for shortcut in shortcuts.getroot().findall("shortcut"):
            # Parse the shortcut, and add it to the list of shortcuts
            item = self._parse_shortcut(shortcut)
            self.all_list_items.append(item[1])

        # Add all visible shortcuts to control 211
        self._display_listitems()

    def _display_listitems(self, focus=None):
        # Displays listitems that are visible from self.all_list_items

        # Initial properties
        count = 0
        visible = False
        self.data_func.clear_label_id()
        listitems = []

        for listitem in self.all_list_items:
            # Get icon overrides
            self._get_icon_overrides(listitem)

            # Set order index in case its changed
            listitem.setProperty("skinshortcuts-orderindex", str(count))

            should_display = True
            # Check for a visibility condition
            if listitem.getProperty("visible-condition"):
                should_display = xbmc.getCondVisibility(listitem.getProperty("visible-condition"))

            if should_display is True:
                visible = True
                listitems.append(listitem)

            # Increase our count
            count += 1

        # If there are no shortcuts, add a blank one
        if visible is False:
            listitem = xbmcgui.ListItem(LANGUAGE(32013), offscreen=True)
            listitem.setArt({
                'icon': "DefaultShortcut.png"
            })
            listitem.setProperty("Path", 'noop')
            listitem.setProperty("icon", "DefaultShortcut.png")
            listitem.setProperty("skinshortcuts-orderindex", str(count))
            listitems.append(listitem)
            self.all_list_items.append(listitem)

        self.getControl(211).reset()
        self.getControl(211).addItems(listitems)
        if focus is not None:
            self.getControl(211).selectItem(focus)
        self._add_additional_properties()

    def _parse_shortcut(self, item):
        # Parse a shortcut node
        local_label = self.data_func.local(item.find("label").text)
        local_label_2 = self.data_func.local(item.find("label2").text)

        # Get icon and thumb (and set to None if there isn't any)
        icon = item.find("icon")

        if icon is not None and icon.text:
            icon = icon.text
        else:
            icon = "DefaultShortcut.png"

        thumb = item.find("thumb")
        if thumb is not None and thumb.text:
            thumb = thumb.text
        else:
            thumb = ""

        # If either local_label[ 2 ] starts with a $, ask Kodi to parse it for us
        if local_label[2].startswith("$"):
            local_label[2] = xbmc.getInfoLabel(local_label[2])
        if local_label_2[2].startswith("$"):
            local_label_2[2] = xbmc.getInfoLabel(local_label_2[2])

        # Create the list item
        listitem = xbmcgui.ListItem(label=local_label[2], label2=local_label_2[2], offscreen=True)
        listitem.setArt({
            'icon': xbmc.getInfoLabel(icon),
            'thumb': xbmc.getInfoLabel(thumb)
        })
        listitem.setProperty("localizedString", local_label[0])
        listitem.setProperty("icon", icon)
        listitem.setProperty("thumbnail", thumb)

        # Set the action
        action = item.find("action").text
        self._add_additionalproperty(listitem, "translatedPath", action)
        if "special://skin/" in action:
            translate = SKIN_PATH
            action = action.replace("special://skin/", translate)

        listitem.setProperty("path", action)
        listitem.setProperty("displayPath", action)

        # Set the disabled property
        if item.find("disabled") is not None:
            listitem.setProperty("skinshortcuts-disabled", "True")
        else:
            listitem.setProperty("skinshortcuts-disabled", "False")

        # If there's an overridden icon, use it
        overridden_icon = item.find("override-icon")
        if overridden_icon is not None:
            listitem.setArt({
                'icon': overridden_icon.text
            })
            listitem.setProperty("icon", overridden_icon.text)
            listitem.setProperty("original-icon", icon)

        # Set the labelID, displayID, shortcutType
        listitem.setProperty("labelID", item.find("labelID").text)
        listitem.setProperty("defaultID", item.find("defaultID").text)
        listitem.setProperty("shortcutType", local_label_2[0])

        # Set any visible condition
        is_visible = True
        visible_condition = item.find("visible")
        if visible_condition is not None:
            listitem.setProperty("visible-condition", visible_condition.text)
            is_visible = xbmc.getCondVisibility(visible_condition.text)

        # Check if the shortcut is locked
        locked = item.find("lock")
        if locked is not None:
            if locked.text.lower() == "true" or locked.text == SKIN_DIR:
                listitem.setProperty("LOCKED", locked.text)

        # Additional properties
        additional_properties = item.find("additional-properties")
        if additional_properties is not None:
            listitem.setProperty("additionalListItemProperties", additional_properties.text)
        else:
            listitem.setProperty("additionalListItemProperties", "[]")
        self._add_additional_properties(listitem)

        return [is_visible, listitem]

    def _add_additional_properties(self, listitem=None):
        all_props = {}
        background_name = None
        background_playlist_name = None

        # If the listitem is None, grab the current listitem from 211
        if listitem is None:
            listitem = self.getControl(211).getSelectedItem()

        if listitem is None:
            return

        # Process current properties
        current_properties = listitem.getProperty("skinshortcuts-allproperties")
        if current_properties != "":
            current_properties = ast.literal_eval(current_properties)
        else:
            current_properties = {}

        # Process all custom properties
        custom_properties = listitem.getProperty("additionalListItemProperties")
        if custom_properties != "":
            custom_properties = ast.literal_eval(custom_properties)
            for custom_property in custom_properties:
                if custom_property[1].startswith("$") and \
                        not custom_property[1].startswith("$SKIN"):
                    # Translate some listItem properties if needed so
                    # they're displayed correctly in the gui
                    all_props[custom_property[0]] = xbmc.getInfoLabel(custom_property[1])
                else:
                    all_props[custom_property[0]] = self.data_func.local(custom_property[1])[2]
                    if custom_property[1].isdigit():
                        all_props["%s-NUM" % (custom_property[0])] = custom_property[1]

                # if this is backgroundName or backgroundPlaylistName,
                # keep them so we can localise them properly
                if custom_property[0] == "background_name":
                    background_name = custom_property[1]
                if custom_property[1] == "backgroundPlaylistName":
                    background_playlist_name = custom_property[1]

        # If we've kept backgroundName, localise it with the updated playlist name
        if background_name is not None and background_playlist_name is not None:
            all_props["backgroundName"] = self.data_func.local(background_name)[2].replace(
                "::PLAYLIST::", background_playlist_name
            )

        # Get fallback properties
        fallback_properties, fallbacks = self.data_func.get_custom_property_fallbacks(self.group)

        # Add fallback properties
        for key in fallback_properties:
            if key not in all_props:
                # Check whether we have a fallback for the value
                for property_match in fallbacks[key]:
                    if has_fallback_property(property_match, all_props):
                        all_props[key] = property_match[0]
                        break

        # Get property requirements
        other_properties, requires, _ = self.data_func.get_property_requires()

        # Remove any properties whose requirements haven't been met
        # pylint: disable=unsubscriptable-object,unsupported-membership-test
        for key in other_properties:
            if key in all_props and key in requires and requires[key] not in all_props:
                # This properties requirements aren't met
                all_props.pop(key)
                if "%s-NUM" % key in all_props:
                    all_props.pop("%s-NUM" % key)

        # Save the new properties to the listitem
        listitem.setProperty("skinshortcuts-allproperties", repr(all_props))
        added, removed, changed = self.dict_differ(all_props, current_properties)
        for key in added:
            listitem.setProperty(key, all_props[key])
        for key in removed:
            if key not in all_props:
                continue
            listitem.setProperty(key, None)
        for key in changed:
            listitem.setProperty(key, all_props[key])

        # Save the new properties to the window
        added, removed, changed = self.dict_differ(all_props, self.window_properties)
        for key in added:
            self.current_window.setProperty(key, all_props[key])
        for key in removed:
            self.current_window.clearProperty(key)
        for key in changed:
            self.current_window.setProperty(key, all_props[key])
        self.window_properties = all_props

    def dict_differ(self, current_dict, past_dict):
        # Get differences between dictionaries
        self.current_dict, self.past_dict = current_dict, past_dict
        set_current, set_past = set(current_dict.keys()), set(past_dict.keys())
        intersect = set_current.intersection(set_past)

        #       Added                    Removed               Changed
        changed = set(o for o in intersect if past_dict[o] != current_dict[o])
        return set_current - intersect, set_past - intersect, changed

    def _get_icon_overrides(self, listitem, set_to_default=True, label_id=None):
        # Start by getting the labelID
        if not label_id:
            label_id = listitem.getProperty("localizedString")
            if label_id is None or label_id == "":
                label_id = listitem.getLabel()
            label_id = self.data_func.get_label_id(self.data_func.local(label_id)[3],
                                                   listitem.getProperty("path"))

        # Retrieve icon
        icon = listitem.getProperty("icon")
        icon_is_var = False

        if listitem.getProperty("untranslatedIcon"):
            icon_is_var = True

        # If the icon is a VAR or an INFO, we're going to translate it
        # and set the untranslatedIcon property
        if icon.startswith("$"):
            listitem.setProperty("untranslatedIcon", icon)
            icon = xbmc.getInfoLabel(icon)
            listitem.setProperty("icon", icon)
            listitem.setArt({
                'icon': 'icon'
            })
            icon_is_var = True
        if icon.startswith("resource://"):
            icon_is_var = True

        # Check for overrides
        tree = self.data_func.get_overrides_skin()
        old_icon, _ = self.data_func.icon_override(tree, icon, self.group, label_id)

        # If the skin doesn't have the icon, replace it with DefaultShortcut.png
        set_default = False
        if (not xbmc.skinHasImage(icon) and set_to_default is True) and not icon_is_var:
            if old_icon is None:
                old_icon = icon
            set_default = True
            icon = "DefaultShortcut.png"

        # If we changed the icon, update the listitem
        if old_icon is not None:
            listitem.setArt({
                'icon': 'icon'
            })
            listitem.setProperty("icon", icon)
            listitem.setProperty("original-icon", old_icon)

        if set_default is True and set_to_default is True:
            # We set this to the default icon, so we need to check if /that/ icon is overridden
            self._get_icon_overrides(listitem, False, label_id)

    def _save_shortcuts(self, system_debug=False, script_debug=False):
        # Entry point to save shortcuts - we will call the _save_shortcuts_function and, if it
        # fails, enable debug options (if not enabled) + recreate the error, then offer to upload
        # debug log (if relevant add-on is installed)

        # Save the shortcuts
        try:
            self._save_shortcuts_function()
            return
        except:
            log(print_exc())
            log("Failed to save shortcuts")

        # We failed to save the shortcuts
        if system_debug or script_debug:
            # Disable any logging we enabled
            disable_logging(system_debug, script_debug)
            offer_log_upload(message_id=32097)
            return

        # Enable any debug logging needed
        system_debug, script_debug = enable_logging()

        if system_debug or script_debug:
            # We enabled one or more of the debug options, re-run this function
            self._save_shortcuts(system_debug, script_debug)
        else:
            offer_log_upload(message_id=32097)

    def _save_shortcuts_function(self):
        # Save shortcuts
        if self.change_made is True:
            log("Saving changes")

            # Create a new tree
            tree = ETree.ElementTree(ETree.Element("shortcuts"))
            root = tree.getroot()

            properties = []

            label_id_changes = []
            label_id_changes_dict = {}

            self.data_func.clear_label_id()

            for listitem in self.all_list_items:

                # If the item has a label or an action,
                # or a specified property from the override is present
                if listitem.getLabel() != LANGUAGE(32013) or \
                        listitem.getProperty("path") != "noop" or \
                        self.has_save_with_property(listitem):
                    # Generate labelID, and mark if it has changed
                    label_id = listitem.getProperty("labelID")

                    # defaultID
                    default_id = listitem.getProperty("defaultID")

                    localized_string = listitem.getProperty("localizedString")
                    if localized_string is None or localized_string == "":
                        local_label = self.data_func.local(listitem.getLabel())
                    else:
                        local_label = self.data_func.local(localized_string)
                    new_label_id = self.data_func.get_label_id(local_label[3],
                                                               listitem.getProperty("path"))
                    if self.group == "mainmenu":
                        label_id_changes.append([label_id, new_label_id, default_id])
                        label_id_changes_dict[label_id] = new_label_id

                    # We want to save this
                    shortcut = ETree.SubElement(root, "shortcut")
                    ETree.SubElement(shortcut, "defaultID").text = default_id

                    # Label and label2
                    ETree.SubElement(shortcut, "label").text = local_label[0]
                    ETree.SubElement(shortcut, "label2").text = \
                        self.data_func.local(listitem.getLabel2())[0]

                    # Icon and thumbnail
                    if listitem.getProperty("untranslatedIcon"):
                        icon = listitem.getProperty("untranslatedIcon")
                    else:
                        if listitem.getProperty("original-icon"):
                            icon = listitem.getProperty("original-icon")
                        else:
                            icon = listitem.getProperty("icon")

                    thumb = listitem.getProperty("thumbnail")

                    ETree.SubElement(shortcut, "icon").text = icon
                    ETree.SubElement(shortcut, "thumb").text = thumb

                    # Action
                    ETree.SubElement(shortcut, "action").text = listitem.getProperty("path")

                    # Visible
                    if listitem.getProperty("visible-condition"):
                        ETree.SubElement(shortcut, "visible").text = \
                            listitem.getProperty("visible-condition")

                    # Disabled
                    if listitem.getProperty("skinshortcuts-disabled") == "True":
                        ETree.SubElement(shortcut, "disabled").text = "True"

                    # Locked
                    if listitem.getProperty("LOCKED"):
                        ETree.SubElement(shortcut, "lock").text = listitem.getProperty("LOCKED")

                    # Additional properties
                    if listitem.getProperty("additionalListItemProperties"):
                        additional_properties = ast.literal_eval(
                            listitem.getProperty("additionalListItemProperties")
                        )
                        if icon != "":
                            additional_properties.append(["icon", icon])
                        if thumb != "":
                            additional_properties.append(["thumb", thumb])
                        properties.append([new_label_id, additional_properties])

            # Check whether this is an additional level
            is_sub_level = False
            if "." in self.group and self.group.rsplit(".", 1)[1].isdigit() and \
                    int(self.group.rsplit(".", 1)[1]) in range(1, 6):
                is_sub_level = True

            # Save the shortcuts
            self.data_func.indent(root)
            path = self.data_func.data_xml_filename(
                DATA_PATH,
                self.data_func.slugify(self.group, True, is_sub_level=is_sub_level)
            )

            tree.write(path.replace(".shortcuts", ".self.data_func.xml"), encoding="UTF-8")

            # Now make any labelID changes
            copy_default_properties = []
            while len(label_id_changes) != 0:
                # Get the first labelID change, and check that we're not changing
                # anything from that
                label_id_from = label_id_changes[0][0]
                label_id_to = label_id_changes[0][1]
                default_id_from = label_id_changes[0][2]

                # If label_id_from is empty. this is a new item so we want to set the
                # From the same as the To
                # (this will ensure any default .shortcuts file is copied across)
                if label_id_from == "" or label_id_from is None:
                    label_id_from = label_id_to

                # Check that there isn't another item in the list whose
                # 'From' is the same as our 'To'
                # - if so, we're going to move our items elsewhere,
                # and move 'em to the correct place later
                # (This ensures we don't overwrite anything incorrectly)
                if len(label_id_changes) != 1:
                    for idx in range(1, len(label_id_changes)):
                        if label_id_changes[idx][0] == label_id_to:
                            temp_location = str(random.randrange(0, 9999999999999999))
                            label_id_changes[0][1] = temp_location
                            label_id_changes.append([temp_location, label_id_to, default_id_from])
                            label_id_to = temp_location
                            break

                # Make the change (0 - the main sub-menu, 1-5 - additional submenus )
                for index in range(0, 6):
                    if index == 0:
                        group_name = label_id_from
                        paths = [
                            [self.data_func.data_xml_filename(DATA_PATH,
                                                              self.data_func.slugify(label_id_from,
                                                                                     True)),
                             "Move"],
                            [self.data_func.data_xml_filename(
                                SKIN_SHORTCUTS_PATH,
                                self.data_func.slugify(default_id_from)
                            ),
                                "Copy"],
                            [self.data_func.data_xml_filename(
                                DEFAULT_PATH,
                                self.data_func.slugify(default_id_from)
                            ),
                                "Copy"],
                            [None, "New"]
                        ]
                        target = self.data_func.data_xml_filename(
                            DATA_PATH,
                            self.data_func.slugify(label_id_to, True)
                        )
                    else:
                        group_strtpl = "%s.%s"
                        group_name = group_strtpl % (label_id_from, str(index))
                        paths = [
                            [self.data_func.data_xml_filename(
                                DATA_PATH,
                                self.data_func.slugify(group_strtpl % (label_id_from, str(index)),
                                                       True, is_sub_level=True)
                            ), "Move"],
                            [self.data_func.data_xml_filename(
                                SKIN_SHORTCUTS_PATH,
                                self.data_func.slugify(group_strtpl % (default_id_from, str(index)),
                                                       is_sub_level=True)
                            ), "Copy"],
                            [self.data_func.data_xml_filename(
                                DEFAULT_PATH,
                                self.data_func.slugify(group_strtpl % (default_id_from, str(index)),
                                                       is_sub_level=True)
                            ), "Copy"]
                        ]
                        target = self.data_func.data_xml_filename(
                            DATA_PATH,
                            self.data_func.slugify(group_strtpl % (label_id_to, str(index)), True,
                                                   is_sub_level=True)
                        )

                    for path in paths:

                        if path[1] == "New":
                            tree = ETree.ElementTree(ETree.Element("shortcuts"))
                            tree.write(target, encoding="UTF-8")
                            log("Creating empty file - %s" % target)
                            break

                        if xbmcvfs.exists(path[0]):
                            # The XML file exists
                            if path[1] == "Move":
                                if path[0] != target:
                                    # Move the original to the target path
                                    log("Moving %s to %s" % (path[0], target))
                                    xbmcvfs.rename(path[0], target)
                            else:
                                # We're copying the file (actually, we'll re-write the file without
                                # any LOCKED elements and with icons/thumbs
                                # adjusted to absolute paths)
                                newtree = ETree.parse(path[0])
                                for newnode in newtree.getroot().findall("shortcut"):
                                    search_node = newnode.find("locked")
                                    if search_node is not None:
                                        newnode.remove(search_node)

                                # Write it to the target
                                self.data_func.indent(newtree.getroot())
                                newtree.write(target, encoding="utf-8")
                                log("Copying %s to %s" % (path[0], target))

                                # We'll need to import it's default properties,
                                # so save the group_name
                                copy_default_properties.append(group_name)
                            break

                label_id_changes.pop(0)

            # Save widgets, backgrounds and custom properties
            self._save_properties(properties, label_id_changes_dict, copy_default_properties)

            # Note that we've saved stuff
            HOME_WINDOW.setProperty("skinshortcuts-reloadmainmenu", "True")

    def has_save_with_property(self, listitem):
        for property_name in self.save_with_property:
            if listitem.getProperty(property_name) != "":
                return True
        return False

    def _save_properties(self, properties, label_id_changes, copy_defaults):
        # Save all additional properties (widgets, backgrounds, custom)
        log("Saving properties")

        current_properties = []

        list_properties = read_properties()
        for list_property in list_properties:
            # list_property[0] = groupname
            # list_property[1] = labelID
            # list_property[2] = property name
            # list_property[3] = property value
            current_properties.append(
                [list_property[0], list_property[1], list_property[2], list_property[3]]
            )

        # Copy any items not in the current group to the array we'll save, and
        # make any labelID changes whilst we're at it
        save_data = []
        for prop in current_properties:
            # [ groupname, itemLabelID, property, value ]
            if not prop[0] == self.group:
                if prop[0] in label_id_changes:
                    prop[0] = label_id_changes[prop[0]]
                elif "." in prop[0] and prop[0].rsplit(".", 1)[1].isdigit():
                    # Additional menu
                    group_name, group_value = prop[0].rsplit(".", 1)
                    if group_name in label_id_changes and int(group_value) in range(1, 6):
                        prop[0] = "%s.%s" % (label_id_changes[group_name], group_value)
                save_data.append(prop)

        # Add all the properties we've been passed
        for prop in properties:
            # prop[0] = labelID
            for to_save in prop[1]:
                # to_save[0] = property name
                # to_save[1] = property value

                save_data.append([self.group, prop[0], to_save[0], to_save[1]])

        # Add any default properties
        for group in copy_defaults:
            for default_property in self.data_func.default_properties:
                # [ groupname, itemLabelID, property, value ]
                if default_property[0] == group:
                    save_data.append(
                        [group, default_property[1], default_property[2], default_property[3]]
                    )

        write_properties(save_data)

        # Clear saved properties in DATA, so it will pick up any new ones next time we load a file
        self.data_func.current_properties = None

    def _load_overrides(self):
        # Load various overrides from the skin, most notably backgrounds and thumbnails
        self.backgrounds = "LOADING"
        self.thumbnails = "LOADING"

        # Load skin overrides
        tree = self.data_func.get_overrides_skin()

        # Should we allow the user to select a playlist as a widget...
        elem = tree.find('widgetPlaylists')
        if elem is not None and elem.text == "True":
            self.widget_playlists = True
            if "type" in elem.attrib:
                self.widget_playlists_type = elem.attrib.get("type")

        # Get backgrounds and thumbnails - we do this in a separate thread as the
        # json used to load VFS paths is very expensive
        thread.start_new_thread(self._load_backgrounds_thumbnails, ())

        # Should we allow the user to browse for background images...
        elem = tree.find('backgroundBrowse')
        if elem is not None and elem.text.lower() in ("true", "single", "multi"):
            self.background_browse = elem.text.lower()
            if "default" in elem.attrib:
                self.background_browse_default = elem.attrib.get("default")

        # Find the default thumbnail browse directory
        elem = tree.find("thumbnailBrowseDefault")
        if elem is not None and len(elem.text) > 0:
            self.thumbnail_browse_default = elem.text

        # Should we allow the user to rename a widget?
        elem = tree.find("widgetRename")
        if elem is not None and elem.text.lower() == "false":
            self.widget_rename = False

        # Does the skin override GUI 308?
        elem = tree.find("alwaysReset")
        if elem is not None and elem.text.lower() == "true":
            self.always_reset = True
        elem = tree.find("alwaysRestore")
        if elem is not None and elem.text.lower() == "true":
            self.always_restore = True

        # Do we enable 'Get More...' button when browsing Skin Helper widgets
        elem = tree.find("defaultwidgetsGetMore")
        if elem is not None and elem.text.lower() == "false":
            self.lib_func.skinhelper_widget_install = False

        # Are there any controls we don't close the window on 'back' for?
        for elem in tree.findall("onback"):
            self.on_back[int(elem.text)] = int(elem.attrib.get("to"))

        # Are there any custom properties that shortcuts should be saved if present
        for elem in tree.findall("saveWithProperty"):
            self.save_with_property.append(elem.text)

    def _load_overrides_context(self):
        # Load context menu settings from overrides
        for override_type in ["skin", "script"]:
            # Load overrides
            if override_type == "skin":
                tree = self.data_func.get_overrides_skin()
            else:
                tree = self.data_func.get_overrides_script()

            # Check if context menu overrides in tree
            elem = tree.find("contextmenu")
            if elem is None:
                # It isn't
                continue

            # Get which controls the context menu is enabled on
            for control in elem.findall("enableon"):
                self.context_controls.append(int(control.text))

            # Get the context menu items
            for item in elem.findall("item"):
                if "control" not in item.attrib:
                    # There's no control specified, so it's no use to us
                    continue

                condition = None
                if "condition" in item.attrib:
                    condition = item.attrib.get("condition")

                self.context_items.append((int(item.attrib.get("control")), condition, item.text))

            # If we get here, we've loaded context options, so we're done
            return

    def _load_overrides_onclick(self):
        # Load additional onlcicks from overrides

        # Get overrides
        tree = self.data_func.get_overrides_skin()

        # Get additional onclick handlers
        for control in tree.findall("onclick"):
            self.custom_on_click[int(control.get("id"))] = control.text

    def _load_backgrounds_thumbnails(self):
        # Load backgrounds (done in background thread)
        backgrounds = []
        thumbnails = []

        # Load skin overrides
        tree = self.data_func.get_overrides_skin()

        # Get backgrounds
        elems = tree.findall('background')
        for elem in elems:
            if "condition" in elem.attrib:
                if not xbmc.getCondVisibility(elem.attrib.get("condition")):
                    continue

            if elem.text.startswith("||BROWSE||"):
                # we want to include images from a VFS path...
                images = self.lib_func.get_images_from_vfs(elem.text.replace("||BROWSE||", ""))
                for image in images:
                    backgrounds.append([image[0], image[1]])
            elif "icon" in elem.attrib:
                backgrounds.append([elem.attrib.get("icon"),
                                    self.data_func.local(elem.attrib.get('label'))[2]])
            else:
                backgrounds.append([elem.text, self.data_func.local(elem.attrib.get('label'))[2]])

        self.backgrounds = backgrounds

        # Get thumbnails
        elems = tree.findall('thumbnail')
        for elem in elems:
            if "condition" in elem.attrib:
                if not xbmc.getCondVisibility(elem.attrib.get("condition")):
                    continue

            if elem.text.startswith("||BROWSE||"):
                # we want to include images from a VFS path...
                images = self.lib_func.get_images_from_vfs(elem.text.replace("||BROWSE||", ""))
                for image in images:
                    thumbnails.append([image[0], image[1]])
            elif elem.text == "::NONE::":
                if "label" in elem.attrib:
                    self.thumbnail_none = elem.attrib.get("label")
                else:
                    self.thumbnail_none = "231"
            else:
                thumbnails.append([elem.text, self.data_func.local(elem.attrib.get('label'))[2]])

        self.thumbnails = thumbnails

    def _load_custom_property_buttons(self):
        # Load a list of addition button IDs we'll handle for setting additional properties

        # Load skin overrides
        tree = self.data_func.get_overrides_skin()

        for elem in tree.findall("propertySettings"):
            if "buttonID" in elem.attrib and "property" in elem.attrib:
                self.custom_property_buttons[int(elem.attrib.get("buttonID"))] = \
                    elem.attrib.get("property")
            elif "buttonID" in elem.attrib and "toggle" in elem.attrib:
                self.custom_toggle_buttons[int(elem.attrib.get("buttonID"))] = \
                    elem.attrib.get("toggle")

    # ========================
    # === GUI INTERACTIONS ===
    # ========================

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if control_id == 102:
            # Move to previous type of shortcuts
            self.shortcutgroup = self.shortcutgroup - 1
            if self.shortcutgroup == 0:
                self.shortcutgroup = self.lib_func.flat_groupings_count()

            self._display_shortcuts()

        elif control_id == 103:
            # Move to next type of shortcuts
            self.shortcutgroup = self.shortcutgroup + 1
            if self.shortcutgroup > self.lib_func.flat_groupings_count():
                self.shortcutgroup = 1

            self._display_shortcuts()

        elif control_id == 111:
            # User has selected an available shortcut they want in their menu
            log("Select shortcut (111)")
            list_control = self.getControl(211)
            item_index = list_control.getSelectedPosition()
            order_index = int(
                list_control.getListItem(item_index).getProperty("skinshortcuts-orderindex")
            )

            if self.warnonremoval(list_control.getListItem(item_index)) is False:
                return

            # Copy the new shortcut
            selected_item = self.getControl(111).getSelectedItem()
            listitem_copy = self._duplicate_listitem(selected_item,
                                                     list_control.getListItem(item_index))

            path = listitem_copy.getProperty("path")
            if path.startswith("||BROWSE||"):
                # If this is a plugin, call our plugin browser
                browse_path = "plugin://%s" % path.replace("||BROWSE||", "")
                return_val = self.lib_func.explorer(
                    [browse_path],
                    browse_path,
                    [self.getControl(111).getSelectedItem().getLabel()],
                    [self.getControl(111).getSelectedItem().getProperty("thumbnail")],
                    self.getControl(111).getSelectedItem().getProperty("shortcutType")
                )
                if return_val is not None:
                    # Convert backslashes to double-backslashes (windows fix)
                    new_action = return_val.getProperty("Path")
                    new_action = new_action.replace("\\", "\\\\")
                    return_val.setProperty("path", new_action)
                    return_val.setProperty("displayPath", new_action)
                    listitem_copy = self._duplicate_listitem(return_val,
                                                             list_control.getListItem(item_index))
                else:
                    listitem_copy = None
            elif path == "||UPNP||":
                return_val = self.lib_func.explorer(
                    ["upnp://"], "upnp://",
                    [self.getControl(111).getSelectedItem().getLabel()],
                    [self.getControl(111).getSelectedItem().getProperty("thumbnail")],
                    self.getControl(111).getSelectedItem().getProperty("shortcutType")
                )
                if return_val is not None:
                    listitem_copy = self._duplicate_listitem(return_val,
                                                             list_control.getListItem(item_index))
                else:
                    listitem_copy = None
            elif path.startswith("||SOURCE||"):
                return_val = self.lib_func.explorer(
                    [path.replace("||SOURCE||", "")],
                    path.replace("||SOURCE||", ""),
                    [self.getControl(111).getSelectedItem().getLabel()],
                    [self.getControl(111).getSelectedItem().getProperty("thumbnail")],
                    self.getControl(111).getSelectedItem().getProperty("shortcutType")
                )
                if return_val is not None:
                    if "upnp://" in return_val.getProperty("Path"):
                        listitem_copy = self._duplicate_listitem(
                            return_val,
                            list_control.getListItem(item_index)
                        )
                    else:
                        return_val = self.lib_func.sourcelink_choice(return_val)
                        if return_val is not None:
                            listitem_copy = self._duplicate_listitem(
                                return_val, list_control.getListItem(item_index)
                            )
                        else:
                            listitem_copy = None
                else:
                    listitem_copy = None
            elif path.startswith("::PLAYLIST"):
                log("Selected playlist")
                if ">" not in path or "VideoLibrary" in path:
                    # Give the user the choice of playing or displaying the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.yesno(LANGUAGE(32040), LANGUAGE(32060), "", "",
                                              LANGUAGE(32061), LANGUAGE(32062))
                    # False: Display
                    # True: Play
                    if not userchoice:
                        listitem_copy.setProperty("path", selected_item.getProperty("action-show"))
                        listitem_copy.setProperty("displayPath",
                                                  selected_item.getProperty("action-show"))
                    else:
                        listitem_copy.setProperty("path", selected_item.getProperty("action-play"))
                        listitem_copy.setProperty("displayPath",
                                                  selected_item.getProperty("action-play"))
                elif ">" in path:
                    # Give the user the choice of playing, displaying or party more for the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.select(LANGUAGE(32060),
                                               [LANGUAGE(32061),
                                                LANGUAGE(32062),
                                                xbmc.getLocalizedString(589)])
                    # 0 - Display
                    # 1 - Play
                    # 2 - Party mode
                    if not userchoice or userchoice == 0:
                        listitem_copy.setProperty("path", selected_item.getProperty("action-show"))
                        listitem_copy.setProperty("displayPath",
                                                  selected_item.getProperty("action-show"))
                    elif userchoice == 1:
                        listitem_copy.setProperty("path", selected_item.getProperty("action-play"))
                        listitem_copy.setProperty("displayPath",
                                                  selected_item.getProperty("action-play"))
                    else:
                        listitem_copy.setProperty("path", selected_item.getProperty("action-party"))
                        listitem_copy.setProperty("displayPath",
                                                  selected_item.getProperty("action-party"))

            if listitem_copy is None:
                # Nothing was selected in the explorer
                return

            self.change_made = True

            # Replace the allListItems listitem with our new list item
            self.all_list_items[order_index] = listitem_copy

            # Delete playlist (TO BE REMOVED!)
            self.lib_func.delete_playlist(list_control.getListItem(item_index).getProperty("path"))

            # Display list items
            self._display_listitems(focus=item_index)

        elif control_id in [301, 1301]:
            # Add a new item
            log("Add item (301)")
            self.change_made = True
            list_control = self.getControl(211)
            num = list_control.getSelectedPosition()
            order_index = int(
                list_control.getListItem(num).getProperty("skinshortcuts-orderindex")
            ) + 1

            # Set default label and action
            listitem = xbmcgui.ListItem(LANGUAGE(32013), offscreen=True)
            listitem.setProperty("Path", 'noop')
            listitem.setProperty("additionalListItemProperties", "[]")

            # Add fallback custom property values
            self._add_additional_properties(listitem)

            # Add new item to both displayed list and list kept in memory
            self.all_list_items.insert(order_index, listitem)
            self._display_listitems(num + 1)

            # If Control 1301 is used we want to add a new item and immediately select a shortcut
            if control_id == 1301:
                xbmc.executebuiltin('SendClick(401)')

        elif control_id == 302:
            # Delete an item
            log("Delete item (302)")

            list_control = self.getControl(211)
            num = list_control.getSelectedPosition()
            order_index = int(list_control.getListItem(num).getProperty("skinshortcuts-orderindex"))

            if self.warnonremoval(list_control.getListItem(num)) is False:
                return

            self.lib_func.delete_playlist(list_control.getListItem(num).getProperty("path"))

            self.change_made = True

            # Remove item from memory list, and reload all list items
            self.all_list_items.pop(order_index)
            self._display_listitems(num)

        elif control_id == 303:
            # Move item up in list
            log("Move up (303)")
            list_control = self.getControl(211)

            item_index = list_control.getSelectedPosition()
            order_index = int(
                list_control.getListItem(item_index).getProperty("skinshortcuts-orderindex")
            )
            if item_index == 0:
                # Top item, can't move it up
                return

            self.change_made = True

            while True:
                # Move the item one up in the list
                self.all_list_items[order_index - 1], self.all_list_items[order_index] = \
                    self.all_list_items[order_index], self.all_list_items[order_index - 1]

                # If we've just moved to the top of the list, break
                if order_index == 1:
                    break

                # Check if the item we've just swapped is visible
                should_break = True
                if self.all_list_items[order_index].getProperty("visible-condition"):
                    should_break = xbmc.getCondVisibility(
                        self.all_list_items[order_index].getProperty("visible-condition")
                    )

                if should_break:
                    break

                order_index -= 1

            # Display the updated order
            self._display_listitems(item_index - 1)

        elif control_id == 304:
            # Move item down in list
            log("Move down (304)")
            list_control = self.getControl(211)

            item_index = list_control.getSelectedPosition()
            order_index = int(
                list_control.getListItem(item_index).getProperty("skinshortcuts-orderindex")
            )

            log("%s : %s" % (str(item_index), str(list_control.size())))

            if item_index == list_control.size() - 1:
                return

            self.change_made = True

            while True:
                # Move the item one up in the list
                self.all_list_items[order_index + 1], self.all_list_items[order_index] = \
                    self.all_list_items[order_index], self.all_list_items[order_index + 1]

                # If we've just moved to the top of the list, break
                if order_index == len(self.all_list_items) - 1:
                    break

                # Check if the item we've just swapped is visible
                should_break = True
                if self.all_list_items[order_index].getProperty("visible-condition"):
                    should_break = xbmc.getCondVisibility(
                        self.all_list_items[order_index].getProperty("visible-condition")
                    )

                if should_break:
                    break

                order_index += 1

            # Display the updated order
            self._display_listitems(item_index + 1)

        elif control_id == 305:
            # Change label
            log("Change label (305)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # Retrieve current label and labelID
            label = listitem.getLabel()

            # If the item is blank, set the current label to empty
            if label == LANGUAGE(32013):
                label = ""

            # Get new label from keyboard dialog
            if is_hebrew(label):
                label = label[::-1]
            keyboard = xbmc.Keyboard(label, xbmc.getLocalizedString(528), False)
            keyboard.doModal()
            if keyboard.isConfirmed():
                label = keyboard.getText()
                if label == "":
                    label = LANGUAGE(32013)
            else:
                return

            self.change_made = True
            self._set_label(listitem, label)

        elif control_id == 306:
            # Change thumbnail
            log("Change thumbnail (306)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # Get new thumbnail from browse dialog
            dialog = xbmcgui.Dialog()
            custom_thumbnail = dialog.browse(2, xbmc.getLocalizedString(1030), 'files', '',
                                             True, False, self.thumbnail_browse_default)

            if custom_thumbnail:
                # Update the thumbnail
                self.change_made = True
                listitem.setArt({
                    'thumb': custom_thumbnail
                })
                listitem.setProperty("thumbnail", custom_thumbnail)
            else:
                return

        elif control_id == 307:
            # Change Action
            log("Change action (307)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            if self.warnonremoval(listitem) is False:
                return

            # Retrieve current action
            action = listitem.getProperty("path")
            if action == "noop":
                action = ""

            if self.current_window.getProperty("custom-grouping"):
                selected_shortcut = self.lib_func.select_shortcut(
                    custom=True,
                    current_action=listitem.getProperty("path"),
                    grouping=self.current_window.getProperty("custom-grouping")
                )
                self.current_window.clearProperty("custom-grouping")
            else:
                selected_shortcut = self.lib_func.select_shortcut(
                    custom=True,
                    current_action=listitem.getProperty("path")
                )

            if not selected_shortcut:
                # User cancelled
                return

            if selected_shortcut.getProperty("chosenPath"):
                action = selected_shortcut.getProperty("chosenPath")
            elif selected_shortcut.getProperty("path"):
                action = selected_shortcut.getProperty("path")

            if action == "":
                action = "noop"

            if listitem.getProperty("path") == action:
                return

            self.change_made = True
            self.lib_func.delete_playlist(listitem.getProperty("path"))

            # Update the action
            listitem.setProperty("path", action)
            listitem.setProperty("displaypath", action)
            listitem.setLabel2(LANGUAGE(32024))
            listitem.setProperty("shortcutType", "32024")

        elif control_id == 308:
            # Reset shortcuts
            log("Reset shortcuts (308)")

            # Ask the user if they want to restore a shortcut, or reset to skin defaults
            if self.always_reset:
                # The skin has disable the restore function, so set response as
                # if user has chose the reset to defaults option
                response = 1
            elif self.always_restore:
                # The skin has disabled the reset function, so set response as
                # if the user has chosen to restore a skin-default shortcut
                response = 0
            else:
                # No skin override, so let user decide to restore or reset
                if not self.data_func.check_if_menus_shared():
                    # Also offer to import from another skin
                    response = xbmcgui.Dialog().select(LANGUAGE(32102),
                                                       [LANGUAGE(32103),
                                                        LANGUAGE(32104),
                                                        "Import from compatible skin"])
                else:
                    response = xbmcgui.Dialog().select(LANGUAGE(32102),
                                                       [LANGUAGE(32103), LANGUAGE(32104)])

            if response == -1:
                # User cancelled
                return

            if response == 0:
                # We're going to restore a particular shortcut
                restore_pretty = []
                restore_items = []

                # Save the labelID list from DATA
                original_label_id_list = self.data_func.label_id_list
                self.data_func.label_id_list = []

                # Get a list of all shortcuts that were originally in the menu and
                # restore label_id_list
                self.data_func.clear_label_id()
                shortcuts = self.data_func.get_shortcuts(self.group,
                                                         default_group=self.default_group,
                                                         defaults_only=True)
                self.data_func.label_id_list = original_label_id_list

                for shortcut in shortcuts.getroot().findall("shortcut"):
                    # Parse the shortcut
                    item = self._parse_shortcut(shortcut)

                    # Check if a shortcuts labelID is already in the list
                    if item[1].getProperty("labelID") not in self.data_func.label_id_list:
                        restore_pretty.append(self.lib_func.create(
                            ["", item[1].getLabel(), item[1].getLabel2(), {
                                "icon": item[1].getProperty("icon")
                            }]
                        ))
                        restore_items.append(item[1])

                if len(restore_items) == 0:
                    xbmcgui.Dialog().ok(LANGUAGE(32103), LANGUAGE(32105))
                    return

                # Let the user select a shortcut to restore
                dialog = ShowDialog("DialogSelect.xml", CWD, listing=restore_pretty,
                                    window_title=LANGUAGE(32103))
                dialog.doModal()
                restore_shortcut = dialog.result
                del dialog

                if restore_shortcut == -1:
                    # User cancelled
                    return

                # We now have our shortcut to return. Add it to self.all_list_items and labelID list
                self.all_list_items.append(restore_items[restore_shortcut])
                self.data_func.label_id_list.append(
                    restore_items[restore_shortcut].getProperty("labelID")
                )

                self.change_made = True
                self._display_listitems()

            if response == 1:
                # We're going to reset all the shortcuts
                self.change_made = True

                # Delete any auto-generated source playlists
                for idx in range(0, self.getControl(211).size()):
                    self.lib_func.delete_playlist(
                        self.getControl(211).getListItem(idx).getProperty("path")
                    )

                self.getControl(211).reset()

                self.all_list_items = []

                # Call the load shortcuts function, but add that we don't want
                # previously saved user shortcuts
                self.load_shortcuts(False)

            # We're going to offer to import menus from another compatible skin
            skin_list, shared_files = self.data_func.get_shared_skin_list()

            if len(skin_list) == 0:
                xbmcgui.Dialog().ok(LANGUAGE(32110), LANGUAGE(32109))
                return

            # Let the user select a shortcut to restore
            import_menu = xbmcgui.Dialog().select(LANGUAGE(32110), skin_list)

            if import_menu == -1:
                # User cancelled
                return

            # Delete any auto-generated source playlists
            for idx in range(0, self.getControl(211).size()):
                self.lib_func.delete_playlist(
                    self.getControl(211).getListItem(idx).getProperty("path")
                )

            if import_menu == 0 and not len(shared_files) == 0:
                # User has chosen to import the shared menu
                self.data_func.import_skin_menu(shared_files)
            else:
                # User has chosen to import from a particular skin
                self.data_func.import_skin_menu(
                    self.data_func.get_files_for_skin(skin_list[import_menu]),
                    skin_list[import_menu]
                )

            self.getControl(211).reset()

            self.all_list_items = []

            # Call the load shortcuts function
            self.load_shortcuts(True)

        elif control_id == 309:
            # Choose widget
            log("Warning: Deprecated control 309 (Choose widget) selected")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # Check that widgets have been loaded
            self.lib_func.load_library("widgets")

            # If we're setting for an additional widget, get it's number
            widget_id = ""
            if self.current_window.getProperty("widgetID"):
                widget_id += ".%s" % self.current_window.getProperty("widgetID")
                self.current_window.clearProperty("widgetID")

            # Get the default widget for this item
            default_widget = self.find_default("widget", listitem.getProperty("labelID"),
                                               listitem.getProperty("defaultID"))

            # Generate list of widgets for select dialog
            widget = [""]
            widget_label = [LANGUAGE(32053)]
            widget_name = [""]
            widget_type = [None]
            for key in self.lib_func.dictionary_groupings["widgets-classic"]:
                widget.append(key[0])
                widget_name.append("")
                widget_type.append(key[2])

                if key[0] == default_widget:
                    widget_label.append("%s (%s)" % (key[1], LANGUAGE(32050)))
                else:
                    widget_label.append(key[1])

            # If playlists have been enabled for widgets, add them too
            if self.widget_playlists:
                # Ensure playlists are loaded
                self.lib_func.load_library("playlists")

                # Add them
                playlist_strtpl = "::PLAYLIST::%s"
                for playlist in self.lib_func.widget_playlists_list:
                    widget.append(playlist_strtpl % playlist[0])
                    widget_label.append(playlist[1])
                    widget_name.append(playlist[2])
                    widget_type.append(self.widget_playlists_type)
                for playlist in self.lib_func.script_playlists():
                    widget.append(playlist_strtpl % playlist[0])
                    widget_label.append(playlist[1])
                    widget_name.append(playlist[2])
                    widget_type.append(self.widget_playlists_type)

            # Show the dialog
            selected_widget = xbmcgui.Dialog().select(LANGUAGE(32044), widget_label)

            if selected_widget == -1:
                # User cancelled
                return
            if selected_widget == 0:
                # User selected no widget
                self._remove_additionalproperty(listitem, "widget%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetName%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetType%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetPlaylist%s" % widget_id)

            else:
                if widget[selected_widget].startswith("::PLAYLIST::"):
                    self._add_additionalproperty(listitem, "widget%s" % widget_id, "Playlist")
                    self._add_additionalproperty(listitem, "widgetName%s" % widget_id,
                                                 widget_name[selected_widget])
                    self._add_additionalproperty(listitem, "widgetPlaylist%s" % widget_id,
                                                 widget[selected_widget].strip("::PLAYLIST::"))
                    if self.current_window.getProperty("useWidgetNameAsLabel") == "true" and \
                            widget_id == "":
                        self._set_label(listitem, widget_name[selected_widget])
                        self.current_window.clearProperty("useWidgetNameAsLabel")
                else:
                    self._add_additionalproperty(
                        listitem, "widgetName%s" % widget_id,
                        widget_label[selected_widget].replace(" (%s)" % (LANGUAGE(32050)), "")
                    )
                    self._add_additionalproperty(listitem, "widget%s" % widget_id,
                                                 widget[selected_widget])
                    self._remove_additionalproperty(listitem, "widgetPlaylist%s" % widget_id)
                    if self.current_window.getProperty("useWidgetNameAsLabel") == "true" and \
                            widget_id == "":
                        self._set_label(
                            listitem,
                            widget_label[selected_widget].replace(" (%s)" % (LANGUAGE(32050)), "")
                        )
                        self.current_window.clearProperty("useWidgetNameAsLabel")

                if widget_type[selected_widget] is not None:
                    self._add_additionalproperty(listitem, "widgetType%s" % widget_id,
                                                 widget_type[selected_widget])
                else:
                    self._remove_additionalproperty(listitem, "widgetType%s" % widget_id)

            self.change_made = True

        elif control_id == 312:
            # Alternative widget select
            log("Choose widget (312)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # If we're setting for an additional widget, get its number
            widget_id = ""
            if self.current_window.getProperty("widgetID"):
                widget_id = ".%s" % self.current_window.getProperty("widgetID")
                self.current_window.clearProperty("widgetID")

            # Get the default widget for this item
            _ = self.find_default("widget", listitem.getProperty("labelID"),
                                  listitem.getProperty("defaultID"))

            # Ensure widgets are loaded
            self.lib_func.load_library("widgets")

            # Let user choose widget
            if listitem.getProperty("widgetPath") == "":
                selected_shortcut = self.lib_func.select_shortcut(grouping="widget", show_none=True)
            else:
                selected_shortcut = self.lib_func.select_shortcut(
                    grouping="widget",
                    show_none=True,
                    custom=True,
                    current_action=listitem.getProperty("widgetPath")
                )

            if selected_shortcut is None:
                # User cancelled
                return

            if selected_shortcut.getProperty("Path") and \
                    selected_shortcut.getProperty("custom") == "true":
                # User has manually edited the widget path, so we'll update that property only
                self._add_additionalproperty(listitem, "widgetPath%s" % widget_id,
                                             selected_shortcut.getProperty("Path"))
                self.change_made = True

            elif selected_shortcut.getProperty("Path"):
                # User has chosen a widget

                # Let user edit widget title, if they want & skin hasn't disabled it
                widget_name = selected_shortcut.getProperty("widgetName")
                if self.widget_rename:
                    if widget_name.startswith("$"):
                        widget_temp_name = xbmc.getInfoLabel(widget_name)
                    else:
                        widget_temp_name = self.data_func.local(widget_name)[2]
                    if is_hebrew(widget_temp_name):
                        widget_temp_name = widget_temp_name[::-1]
                    keyboard = xbmc.Keyboard(widget_temp_name,
                                             xbmc.getLocalizedString(16105),
                                             False)
                    keyboard.doModal()
                    if (keyboard.isConfirmed()) and keyboard.getText() != "":
                        if widget_temp_name != keyboard.getText():
                            widget_name = keyboard.getText()

                # Add any necessary reload parameter
                widget_path = \
                    self.lib_func.add_widget_reload(selected_shortcut.getProperty("widgetPath"))

                self._add_additionalproperty(listitem, "widget%s" % widget_id,
                                             selected_shortcut.getProperty("widget"))
                self._add_additionalproperty(listitem, "widgetName%s" % widget_id, widget_name)
                self._add_additionalproperty(listitem, "widgetType%s" % widget_id,
                                             selected_shortcut.getProperty("widgetType"))
                self._add_additionalproperty(listitem, "widgetTarget%s" % widget_id,
                                             selected_shortcut.getProperty("widgetTarget"))
                self._add_additionalproperty(listitem, "widgetPath%s" % widget_id, widget_path)
                if self.current_window.getProperty("useWidgetNameAsLabel") == "true" and \
                        widget_id == "":
                    self._set_label(listitem, selected_shortcut.getProperty("widgetName"))
                    self.current_window.clearProperty("useWidgetNameAsLabel")
                self.change_made = True

            else:
                # User has selected 'None'
                self._remove_additionalproperty(listitem, "widget%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetName%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetType%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetTarget%s" % widget_id)
                self._remove_additionalproperty(listitem, "widgetPath%s" % widget_id)
                if self.current_window.getProperty("useWidgetNameAsLabel") == "true" and \
                        widget_id == "":
                    self._set_label(listitem, selected_shortcut.getProperty("widgetName"))
                    self.current_window.clearProperty("useWidgetNameAsLabel")
                self.change_made = True

                return

        elif control_id == 310:
            # Choose background
            log("Choose background (310)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            pretty_dialog = False

            # Create lists for the select dialog, with image browse buttons if enabled
            if self.background_browse == "true":
                log("Adding both browse options")
                background = ["", "", ""]
                background_label = [LANGUAGE(32053), LANGUAGE(32051), LANGUAGE(32052)]
                background_pretty = [self.lib_func.create(["", LANGUAGE(32053), "", {
                    "icon": "DefaultAddonNone.png"
                }]), self.lib_func.create(["", LANGUAGE(32051), "", {
                    "icon": "DefaultFile.png"
                }]), self.lib_func.create(["", LANGUAGE(32052), "", {
                    "icon": "DefaultFolder.png"
                }])]
            elif self.background_browse == "single":
                log("Adding single browse option")
                background = ["", ""]
                background_label = [LANGUAGE(32053), LANGUAGE(32051)]
                background_pretty = [self.lib_func.create(["", LANGUAGE(32053), "", {
                    "icon": "DefaultAddonNone.png"
                }]), self.lib_func.create(["", LANGUAGE(32051), "", {
                    "icon": "DefaultFile.png"
                }])]
            elif self.background_browse == "multi":
                log("Adding multi browse option")
                background = ["", ""]
                background_label = [LANGUAGE(32053), LANGUAGE(32052)]
                background_pretty = [self.lib_func.create(["", LANGUAGE(32053), "", {
                    "icon": "DefaultAddonNone.png"
                }]), self.lib_func.create(["", LANGUAGE(32052), "", {
                    "icon": "DefaultFolder.png"
                }])]
            else:
                background = [""]
                background_label = [LANGUAGE(32053)]
                background_pretty = [self.lib_func.create(["", LANGUAGE(32053), "", {
                    "icon": "DefaultAddonNone.png"
                }])]

            # Wait to ensure that all backgrounds are loaded
            count = 0
            while self.backgrounds == "LOADING" and count < 20:
                if xbmc.Monitor().waitForAbort(0.1):
                    return
                count = count + 1
            if self.backgrounds == "LOADING":
                self.backgrounds = []

            # Get the default background for this item
            default_background = self.find_default("background", listitem.getProperty("labelID"),
                                                   listitem.getProperty("defaultID"))

            # Generate list of backgrounds for the dialog
            for key in self.backgrounds:
                if "::PLAYLIST::" in key[1]:
                    for playlist in self.lib_func.widget_playlists_list:
                        background.append([key[0], playlist[0], playlist[1]])
                        background_label.append(key[1].replace("::PLAYLIST::", playlist[1]))
                        background_pretty.append(
                            self.lib_func.create(
                                ["", key[1].replace("::PLAYLIST::", playlist[1]), "", {}]
                            )
                        )
                    for playlist in self.lib_func.script_playlists():
                        background.append([key[0], playlist[0], playlist[1]])
                        background_label.append(key[1].replace("::PLAYLIST::", playlist[1]))
                        background_pretty.append(
                            self.lib_func.create(
                                ["", key[1].replace("::PLAYLIST::", playlist[1]), "", {}]
                            )
                        )
                else:
                    background.append(key[0])
                    virtual_image = None
                    if key[0].startswith("$INFO") or key[0].startswith("$VAR"):
                        virtual_image = key[0].replace("$INFO[", "").replace("$VAR[", "") \
                            .replace("]", "")
                        virtual_image = xbmc.getInfoLabel(virtual_image)

                    # fix for resource addon images
                    if key[0].startswith("resource://"):
                        virtual_image = key[0]

                    label = key[1]
                    if label.startswith("$INFO") or label.startswith("$VAR"):
                        label = xbmc.getInfoLabel(label)

                    if default_background == key[0]:
                        label = "%s (%s)" % (label, LANGUAGE(32050))

                    background_label.append(label)
                    if xbmc.skinHasImage(key[0]) or virtual_image:
                        pretty_dialog = True
                        background_pretty.append(self.lib_func.create(["", label, "", {
                            "icon": key[0]
                        }]))
                    else:
                        background_pretty.append(self.lib_func.create(["", label, "", {}]))

            if pretty_dialog:
                dialog = ShowDialog("DialogSelect.xml", CWD, listing=background_pretty,
                                    window_title=LANGUAGE(32045))
                dialog.doModal()
                selected_background = dialog.result
                del dialog
            else:
                # Show the dialog
                selected_background = xbmcgui.Dialog().select(LANGUAGE(32045), background_label)

            if selected_background == -1:
                # User cancelled
                return
            if selected_background == 0:
                # User selected no background
                self._remove_additionalproperty(listitem, "background")
                self._remove_additionalproperty(listitem, "backgroundName")
                self._remove_additionalproperty(listitem, "backgroundPlaylist")
                self._remove_additionalproperty(listitem, "backgroundPlaylistName")
                self.change_made = True
                return

            if self.background_browse and (selected_background == 1 or
                                           (self.background_browse == "true" and
                                            selected_background == 2)):
                # User has chosen to browse for an image/folder
                imagedialog = xbmcgui.Dialog()
                if selected_background == 1 and self.background_browse != "multi":  # Single image
                    custom_image = imagedialog.browse(2, xbmc.getLocalizedString(1030), 'files',
                                                      '', True, False,
                                                      self.background_browse_default)
                else:  # Multi-image
                    custom_image = imagedialog.browse(0, xbmc.getLocalizedString(1030), 'files',
                                                      '', True, False,
                                                      self.background_browse_default)

                if custom_image:
                    self._add_additionalproperty(listitem, "background", custom_image)
                    self._add_additionalproperty(listitem, "backgroundName", custom_image)
                    self._remove_additionalproperty(listitem, "backgroundPlaylist")
                    self._remove_additionalproperty(listitem, "backgroundPlaylistName")
                else:
                    # User cancelled
                    return

            else:
                if isinstance(background[selected_background], list):
                    # User has selected a playlist backgrounds
                    self._add_additionalproperty(listitem, "background",
                                                 background[selected_background][0])
                    self._add_additionalproperty(
                        listitem,
                        "backgroundName",
                        background_label[selected_background].replace(
                            "::PLAYLIST::",
                            background[selected_background][1]
                        )
                    )
                    self._add_additionalproperty(listitem, "backgroundPlaylist",
                                                 background[selected_background][1])
                    self._add_additionalproperty(listitem, "backgroundPlaylistName",
                                                 background[selected_background][2])

                else:
                    # User has selected a normal background
                    self._add_additionalproperty(listitem, "background",
                                                 background[selected_background])
                    self._add_additionalproperty(
                        listitem,
                        "backgroundName",
                        background_label[selected_background].replace(
                            " (%s)" % (LANGUAGE(32050)), ""
                        )
                    )
                    self._remove_additionalproperty(listitem, "backgroundPlaylist")
                    self._remove_additionalproperty(listitem, "backgroundPlaylistName")

            self.change_made = True

        elif control_id == 311:
            # Choose thumbnail
            log("Choose thumbnail (311)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # Create lists for the select dialog
            thumbnail = [""]
            thumbnail_label = [self.lib_func.create(["", LANGUAGE(32096), "", {}])]

            # Add a None option if the skin specified it
            if self.thumbnail_none:
                thumbnail.append("")
                thumbnail_label.insert(0, self.lib_func.create(["", self.thumbnail_none, "", {}]))

            # Ensure thumbnails have been loaded
            count = 0
            while self.thumbnails == "LOADING" and count < 20:
                if xbmc.Monitor().waitForAbort(0.1):
                    return
                count = count + 1
            if self.thumbnails == "LOADING":
                self.thumbnails = []

            # Generate list of thumbnails for the dialog
            for key in self.thumbnails:
                log("%s %s" % (repr(key[0]), repr(key[1])))
                thumbnail.append(key[0])
                thumbnail_label.append(self.lib_func.create(["", key[1], "", {
                    "icon": key[0]
                }]))

            # Show the dialog
            dialog = ShowDialog("DialogSelect.xml", CWD, listing=thumbnail_label,
                                window_title="Select thumbnail")
            dialog.doModal()
            selected_thumbnail = dialog.result
            del dialog

            if selected_thumbnail == -1:
                # User cancelled
                return

            if self.thumbnail_none and selected_thumbnail == 0:
                # User has chosen 'None'
                listitem.setArt({
                    'thumb': None
                })
                listitem.setProperty("thumbnail", None)

            elif (not self.thumbnail_none and selected_thumbnail == 0) or \
                    (self.thumbnail_none and selected_thumbnail == 1):
                # User has chosen to browse for an image
                imagedialog = xbmcgui.Dialog()

                if self.thumbnail_browse_default:
                    custom_image = imagedialog.browse(2, xbmc.getLocalizedString(1030), 'files',
                                                      '', True, False,
                                                      self.thumbnail_browse_default)
                else:
                    custom_image = imagedialog.browse(2, xbmc.getLocalizedString(1030), 'files',
                                                      '', True, False,
                                                      self.background_browse_default)

                if custom_image:
                    listitem.setArt({
                        'thumb': custom_image
                    })
                    listitem.setProperty("thumbnail", custom_image)
                else:
                    # User cancelled
                    return

            else:
                # User has selected a normal thumbnail
                listitem.setArt({
                    'thumb': thumbnail[selected_thumbnail]
                })
                listitem.setProperty("thumbnail", thumbnail[selected_thumbnail])
            self.change_made = True

        elif control_id == 313:
            # Toggle disabled
            log("Toggle disabled (313)")
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            # Retrieve and toggle current disabled state
            disabled = listitem.getProperty("skinshortcuts-disabled")
            if disabled == "True":
                listitem.setProperty("skinshortcuts-disabled", "False")
            else:
                # Display any warning
                if self.warnonremoval(listitem) is False:
                    return

                # Toggle to true, add highlighting to label
                listitem.setProperty("skinshortcuts-disabled", "True")

            self.change_made = True

        elif control_id == 401:
            # Select shortcut
            log("Select shortcut (401)")
            num = self.getControl(211).getSelectedPosition()
            order_index = int(
                self.getControl(211).getListItem(num).getProperty("skinshortcuts-orderindex")
            )

            if self.warnonremoval(self.getControl(211).getListItem(num)) is False:
                return

            if self.current_window.getProperty("custom-grouping"):
                selected_shortcut = self.lib_func.select_shortcut(
                    grouping=self.current_window.getProperty("custom-grouping")
                )
                self.current_window.clearProperty("custom-grouping")
            else:
                selected_shortcut = self.lib_func.select_shortcut()

            if selected_shortcut is not None:
                listitem_copy = self._duplicate_listitem(selected_shortcut,
                                                         self.getControl(211).getListItem(num))

                # add a translated version of the path as property
                self._add_additionalproperty(listitem_copy, "translatedPath",
                                             selected_shortcut.getProperty("path"))

                if selected_shortcut.getProperty("smartShortcutProperties"):
                    for listitem_property in ast.literal_eval(
                            selected_shortcut.getProperty("smartShortcutProperties")
                    ):
                        self._add_additionalproperty(listitem_copy, listitem_property[0],
                                                     listitem_property[1])

                # set default background for this item (if any)
                default_background = self.find_default_background(
                    listitem_copy.getProperty("labelID"),
                    listitem_copy.getProperty("defaultID")
                )
                if default_background:
                    self._add_additionalproperty(listitem_copy, "background",
                                                 default_background["path"])
                    self._add_additionalproperty(listitem_copy, "backgroundName",
                                                 default_background["label"])

                # set default widget for this item (if any)
                default_widget = self.find_default_widget(listitem_copy.getProperty("labelID"),
                                                          listitem_copy.getProperty("defaultID"))
                if default_widget:
                    self._add_additionalproperty(listitem_copy, "widget",
                                                 default_widget["widget"])
                    self._add_additionalproperty(listitem_copy, "widgetName",
                                                 default_widget["name"])
                    self._add_additionalproperty(listitem_copy, "widgetType",
                                                 default_widget["type"])
                    self._add_additionalproperty(listitem_copy, "widgetPath",
                                                 default_widget["path"])
                    self._add_additionalproperty(listitem_copy, "widgetTarget",
                                                 default_widget["target"])

                if selected_shortcut.getProperty("chosenPath"):
                    listitem_copy.setProperty("path",
                                              selected_shortcut.getProperty("chosenPath"))
                    listitem_copy.setProperty("displayPath",
                                              selected_shortcut.getProperty("chosenPath"))
                self.lib_func.delete_playlist(
                    self.getControl(211).getListItem(num).getProperty("path")
                )

                self.change_made = True

                self.all_list_items[order_index] = listitem_copy
                self._display_listitems(num)
            else:
                return

        elif control_id in (405, 406, 407, 408, 409, 410):
            # Launch management dialog for submenu
            if HOME_WINDOW.getProperty("skinshortcuts-loading") and \
                    int(calendar.timegm(gmtime())) - \
                    int(HOME_WINDOW.getProperty("skinshortcuts-loading")) <= 5:
                return

            log("Launching management dialog for submenu/additional menu (%s)" % str(control_id))
            HOME_WINDOW.setProperty("skinshortcuts-loading",
                                    str(calendar.timegm(gmtime())))

            # Get the group we're about to edit
            launch_group = self.getControl(211).getSelectedItem().getProperty("labelID")
            launch_default_group = self.getControl(211).getSelectedItem().getProperty("defaultID")
            group_name = self.getControl(211).getSelectedItem().getLabel()

            if launch_default_group is None:
                launch_default_group = ""

            # If the labelID property is empty, we need to generate one
            if launch_group is None or launch_group == "":
                self.data_func.clear_label_id()
                num = self.getControl(211).getSelectedPosition()
                order_index = self.getControl(211).getListItem(num)

                # Get the labelID's of all other menu items
                for listitem in self.all_list_items:
                    if listitem != order_index:
                        self.data_func.get_label_id(listitem.getProperty("labelID"),
                                                    listitem.getProperty("path"))

                # Now generate labelID for this menu item, if it doesn't have one
                label_id = self.getControl(211).getListItem(num).getProperty("localizedString")
                if label_id is None or label_id == "":
                    launch_group = self.data_func.get_label_id(
                        self.getControl(211).getListItem(num).getLabel(),
                        self.getControl(211).getListItem(num).getProperty("path")
                    )
                else:
                    launch_group = self.data_func.get_label_id(
                        label_id,
                        self.getControl(211).getListItem(num).getProperty("path")
                    )
                self.getControl(211).getListItem(num).setProperty("labelID", launch_group)

            # Check if we're launching a specific additional menu
            group_strtpl = "%s.%s"
            if control_id == 406:
                launch_group = group_strtpl % (launch_group, "1")
                launch_default_group = group_strtpl % (launch_default_group, "1")
            elif control_id == 407:
                launch_group = group_strtpl % (launch_group, "2")
                launch_default_group = group_strtpl % (launch_default_group, "2")
            elif control_id == 408:
                launch_group = group_strtpl % (launch_group, "3")
                launch_default_group = group_strtpl % (launch_default_group, "3")
            elif control_id == 409:
                launch_group = group_strtpl % (launch_group, "4")
                launch_default_group = group_strtpl % (launch_default_group, "4")
            elif control_id == 410:
                launch_group = group_strtpl % (launch_group, "5")
                launch_default_group = group_strtpl % (launch_default_group, "5")
            # Check if 'level' property has been set
            elif self.current_window.getProperty("level"):
                launch_group = "%s.%s" % (launch_group, self.current_window.getProperty("level"))
                self.current_window.clearProperty("level")

            # Check if 'groupname' property has been set
            if self.current_window.getProperty("overrideName"):
                group_name = self.current_window.getProperty("overrideName")
                self.current_window.clearProperty("overrideName")

            # Execute the script
            self.current_window.setProperty("additionalDialog", "True")
            dialog = GUI("script-skinshortcuts.xml", CWD, "default", group=launch_group,
                         default_group=launch_default_group, nolabels=self.nolabels,
                         groupname=group_name)
            dialog.doModal()
            del dialog
            self.current_window.clearProperty("additionalDialog")

        if control_id in self.custom_toggle_buttons:
            # Toggle a custom property
            log("Toggling custom property (%s)" % (str(control_id)))
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            property_name = self.custom_toggle_buttons[control_id]
            self.change_made = True

            if listitem.getProperty(property_name) == "True":
                self._remove_additionalproperty(listitem, property_name)
            else:
                self._add_additionalproperty(listitem, property_name, "True")

        if control_id == 404 or control_id in self.custom_property_buttons:
            # Set custom property
            # We do this last so that, if the skinner has specified a default
            # Skin Shortcuts control is used to set the
            # property, that is completed before we get here.
            log("Setting custom property (%s)" % (str(control_id)))
            list_control = self.getControl(211)
            listitem = list_control.getSelectedItem()

            pretty_dialog = False

            # Retrieve the custom property
            if self.current_window.getProperty("customProperty"):
                property_name = self.current_window.getProperty("customProperty")
                self.current_window.clearProperty("customProperty")
                property_value = self.current_window.getProperty("customValue")
                self.current_window.clearProperty("customValue")

                if property_name == "thumb":
                    # Special treatment if we try to set the thumb with the property method
                    listitem.setArt({
                        'icon': xbmc.getInfoLabel(property_value),
                        'thumb': xbmc.getInfoLabel(property_value)
                    })
                    listitem.setProperty("thumbnail", property_value)
                    listitem.setProperty("icon", property_value)
                    if not property_value:
                        listitem.setProperty("original-icon", None)
                elif not property_value:
                    # No value set, so remove it from additionalListItemProperties
                    self._remove_additionalproperty(listitem, property_name)
                else:
                    # Set the property
                    self._add_additionalproperty(listitem, property_name, property_value)

                # notify that we have changes
                self.change_made = True

            elif control_id != 404 or self.current_window.getProperty("chooseProperty"):
                if control_id == 404:
                    # Button 404, so we get the property from the window property
                    property_name = self.current_window.getProperty("chooseProperty")
                    self.current_window.clearProperty("chooseProperty")
                else:
                    # Custom button, so we get the property from the dictionary
                    property_name = self.custom_property_buttons[control_id]

                # Get the overrides
                tree = self.data_func.get_overrides_skin()

                # Set options
                dialog_title = LANGUAGE(32101)
                show_none = True
                image_browse = False
                browse_single = False
                browse_multi = False
                for elem in tree.findall("propertySettings"):
                    # Get property settings based on property value matching
                    if "property" in elem.attrib and elem.attrib.get("property") == property_name:
                        if "title" in elem.attrib:
                            dialog_title = elem.attrib.get("title")
                        if "showNone" in elem.attrib and \
                                elem.attrib.get("showNone").lower() == "false":
                            show_none = False
                        if "imageBrowse" in elem.attrib and \
                                elem.attrib.get("imageBrowse").lower() == "true":
                            image_browse = True

                # Create lists for the select dialog
                prop = []
                property_label = []
                property_pretty = []

                if show_none:
                    # Add a 'None' option to the list
                    prop.append("")
                    property_label.append(LANGUAGE(32053))
                    property_pretty.append(self.lib_func.create(["", LANGUAGE(32053), "", {
                        "icon": "DefaultAddonNone.png"
                    }]))
                if image_browse:
                    # Add browse single/multi options to the list
                    prop.extend(["", ""])
                    property_label.extend([LANGUAGE(32051), LANGUAGE(32052)])
                    property_pretty.extend([self.lib_func.create(["", LANGUAGE(32051), "", {
                        "icon": "DefaultFile.png"
                    }]), self.lib_func.create(["", LANGUAGE(32052), "", {
                        "icon": "DefaultFolder.png"
                    }])])

                # Get all the skin-defined properties
                for elem in tree.findall("property"):
                    if "property" in elem.attrib and elem.attrib.get("property") == property_name:
                        if "condition" in elem.attrib and \
                                not xbmc.getCondVisibility(elem.attrib.get("condition")):
                            continue
                        found_property = elem.text
                        prop.append(found_property)
                        if "icon" in elem.attrib:
                            pretty_dialog = True
                            icon_image = {
                                "icon": elem.attrib.get("icon")
                            }
                        else:
                            icon_image = {}

                        if "label" in elem.attrib:
                            label_value = elem.attrib.get("label")
                            if label_value.startswith("$INFO") or \
                                    label_value.startswith("$VAR") or \
                                    label_value.startswith("$NUMBER"):
                                property_label.append(xbmc.getInfoLabel(label_value))
                                property_pretty.append(
                                    self.lib_func.create(
                                        ["", xbmc.getInfoLabel(label_value), "", icon_image]
                                    )
                                )
                            else:
                                property_label.append(self.data_func.local(label_value)[2])
                                property_pretty.append(
                                    self.lib_func.create(["", label_value, "", icon_image])
                                )
                        else:
                            property_label.append(self.data_func.local(found_property)[2])
                            property_pretty.append(
                                self.lib_func.create(["", found_property, "", icon_image])
                            )

                # Show the dialog
                if pretty_dialog:
                    dialog = ShowDialog("DialogSelect.xml", CWD, listing=property_pretty,
                                        window_title=dialog_title)
                    dialog.doModal()
                    selected_property = dialog.result
                    del dialog
                else:
                    selected_property = xbmcgui.Dialog().select(dialog_title, property_label)

                if selected_property == -1:
                    # User cancelled
                    return
                if selected_property == 0 and show_none:
                    # User selected no property
                    self.change_made = True
                    self._remove_additionalproperty(listitem, property_name)
                elif (selected_property == 0 and not show_none and image_browse) or \
                        (selected_property == 1 and show_none and image_browse):
                    # User has selected to browse for a single image
                    browse_single = True
                elif (selected_property == 1 and not show_none and image_browse) or \
                        (selected_property == 2 and show_none and image_browse):
                    # User has selected to browse for a multi-image
                    browse_multi = True
                else:
                    self.change_made = True
                    self._add_additionalproperty(listitem, property_name, prop[selected_property])

                if browse_single or browse_multi:
                    # User has chosen to browse for an image/folder
                    imagedialog = xbmcgui.Dialog()
                    if browse_single:  # Single image
                        custom_image = imagedialog.browse(2, xbmc.getLocalizedString(1030),
                                                          'files', '', True, False)
                    else:  # Multi-image
                        custom_image = imagedialog.browse(0, xbmc.getLocalizedString(1030),
                                                          'files', '', True, False)

                    if custom_image:
                        self.change_made = True
                        self._add_additionalproperty(listitem, property_name, custom_image)
                    else:
                        # User cancelled
                        return

            else:
                # The customProperty or chooseProperty window properties needs to be set, so return
                self.current_window.clearProperty("customValue")
                return

        # Custom onclick actions
        if control_id in self.custom_on_click:
            xbmc.executebuiltin(self.custom_on_click[control_id])

    # ========================
    # === HELPER FUNCTIONS ===
    # ========================

    def _display_shortcuts(self):
        # Load the currently selected shortcut group
        new_group = self.lib_func.retrieve_group(self.shortcutgroup)

        label = self.data_func.local(new_group[0])[2]

        self.getControl(111).reset()
        for item in new_group[1]:
            new_item = self._duplicate_listitem(item)
            if item.getProperty("action-show"):
                new_item.setProperty("action-show", item.getProperty("action-show"))
                new_item.setProperty("action-play", item.getProperty("action-play"))
                new_item.setProperty("action-party", item.getProperty("action-party"))
            self.getControl(111).addItem(new_item)
        self.getControl(101).setLabel("%s (%s)" % (label, self.getControl(111).size()))

    def _duplicate_listitem(self, listitem, originallistitem=None):
        # Create a copy of an existing listitem
        listitem_copy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(),
                                         offscreen=True)
        listitem.setArt({
            'icon': listitem.getProperty("icon"),
            'thumb': listitem.getProperty("thumbnail")
        })
        listitem_copy.setProperty("path", listitem.getProperty("path"))
        listitem_copy.setProperty("displaypath", listitem.getProperty("path"))
        listitem_copy.setProperty("icon", listitem.getProperty("icon"))
        listitem_copy.setProperty("thumbnail", listitem.getProperty("thumbnail"))
        listitem_copy.setProperty("localizedString", listitem.getProperty("localizedString"))
        listitem_copy.setProperty("shortcutType", listitem.getProperty("shortcutType"))
        listitem_copy.setProperty("skinshortcuts-disabled",
                                  listitem.getProperty("skinshortcuts-disabled"))

        if listitem.getProperty("LOCKED"):
            listitem_copy.setProperty("LOCKED", listitem.getProperty("LOCKED"))

        if listitem.getProperty("defaultID"):
            listitem_copy.setProperty("defaultID", listitem.getProperty("defaultID"))
        elif listitem.getProperty("labelID"):
            listitem_copy.setProperty("defaultID", listitem.getProperty("labelID"))
        else:
            listitem_copy.setProperty(
                "defaultID",
                self.data_func.get_label_id(
                    self.data_func.local(listitem.getProperty("localizedString"))[3],
                    listitem.getProperty("path"),
                    True
                )
            )

        # If the item has an untranslated icon, set the icon image to it
        if listitem.getProperty("untranslatedIcon"):
            icon = listitem.getProperty("untranslatedIcon")
            listitem_copy.setArt({
                'icon': 'icon'
            })
            listitem_copy.setProperty("icon", icon)

        # Revert to original icon (because we'll override it again in a minute!)
        if listitem.getProperty("original-icon"):
            icon = listitem.getProperty("original-icon")
            if icon == "":
                icon = None
            listitem_copy.setArt({
                'icon': 'icon'
            })
            listitem_copy.setProperty("icon", icon)

        # If we've haven't been passed an originallistitem, set the following
        # from the listitem we were passed
        if originallistitem is None:
            listitem_copy.setProperty("labelID", listitem.getProperty("labelID"))
            if listitem.getProperty("visible-condition"):
                listitem_copy.setProperty("visible-condition",
                                          listitem.getProperty("visible-condition"))
            if listitem.getProperty("additionalListItemProperties"):
                listitem_copy.setProperty("additionalListItemProperties",
                                          listitem.getProperty("additionalListItemProperties"))
        else:
            # Set these from the original item we were passed
            # (this will keep original labelID and additional properties in tact)
            listitem_copy.setProperty("labelID", originallistitem.getProperty("labelID"))
            if originallistitem.getProperty("visible-condition"):
                listitem_copy.setProperty("visible-condition",
                                          originallistitem.getProperty("visible-condition"))
            if originallistitem.getProperty("additionalListItemProperties"):
                listitem_copy.setProperty(
                    "additionalListItemProperties",
                    originallistitem.getProperty("additionalListItemProperties")
                )

        # Add custom properties
        self._add_additional_properties(listitem_copy)

        return listitem_copy

    def _add_additionalproperty(self, listitem, property_name, property_value):
        # Add an item to the additional properties of a user items
        properties = []
        if listitem.getProperty("additionalListItemProperties"):
            properties = ast.literal_eval(listitem.getProperty("additionalListItemProperties"))

        found_property = False
        for idx, prop in enumerate(properties):
            if prop[0] == property_name:
                found_property = True
                properties[idx][1] = self.data_func.local(property_value)[0]

        if found_property is False:
            properties.append([property_name, self.data_func.local(property_value)[0]])

        # translate any INFO labels (if needed) so they will be displayed correctly in the gui
        if property_value:
            if property_value.startswith("$") and not property_value.startswith("$SKIN"):
                listitem.setProperty(property_name, xbmc.getInfoLabel(property_value))
            else:
                listitem.setProperty(property_name, self.data_func.local(property_value)[2])
                if property_value.isdigit():
                    listitem.setProperty("%s-NUM" % property_name, property_value)

        listitem.setProperty("additionalListItemProperties", repr(properties))

        self._add_additional_properties(listitem)

    def _remove_additionalproperty(self, listitem, property_name):
        # Remove an item from the additional properties of a user item
        properties = []
        if listitem.getProperty("additionalListItemProperties"):
            properties = ast.literal_eval(listitem.getProperty("additionalListItemProperties"))

        for prop in properties:
            if prop[0] == property_name or "%s-NUM" % (prop[0]) == "%s-NUM" % property_name:
                listitem.setProperty(prop[0], None)
                properties.remove(prop)

        listitem.setProperty("additionalListItemProperties", repr(properties))

        self._add_additional_properties(listitem)

    def warnonremoval(self, item):
        # This function will warn the user before they modify a settings link
        # (if the skin has enabled this function)
        tree = self.data_func.get_overrides_skin()

        for elem in tree.findall("warn"):
            if elem.text.lower() == item.getProperty("displaypath").lower():
                # We want to show the message :)
                message = self.data_func.local(elem.attrib.get("message"))[2]

                heading = self.data_func.local(elem.attrib.get("heading"))[2]

                dialog = xbmcgui.Dialog()
                return dialog.yesno(heading, message)

        return True

    def find_default_background(self, label_id, default_id):
        # This function finds the default background, including properties
        result = {}
        count = 0
        while self.backgrounds == "LOADING" and count < 20:
            if xbmc.Monitor().waitForAbort(0.1):
                return result
            count = count + 1
        if self.backgrounds == "LOADING":
            self.backgrounds = []

        default_background = self.find_default("background", label_id, default_id)
        if default_background:
            for key in self.backgrounds:
                if default_background == key[0]:
                    result["path"] = key[0]
                    result["label"] = key[1]
                elif default_background == key[1]:
                    result["path"] = key[0]
                    result["label"] = key[1]

        return result

    def find_default_widget(self, label_id, default_id):
        # This function finds the default widget, including properties
        result = {}

        # first look for any widgetdefaultnodes
        default_widget = self.find_default("widgetdefaultnode", label_id, default_id)
        if default_widget is not None:
            result["path"] = default_widget.get("path")
            result["name"] = default_widget.get("label")
            result["widget"] = default_widget.text
            result["type"] = default_widget.get("type")
            result["target"] = default_widget.get("target")
        else:
            # find any classic widgets
            default_widget = self.find_default("widget", label_id, default_id)
            for key in self.lib_func.dictionary_groupings["widgets-classic"]:
                if key[0] == default_widget:
                    result["widget"] = key[0]
                    result["name"] = key[1]
                    result["type"] = key[2]
                    result["path"] = key[3]
                    result["target"] = key[5]
                    break
        return result

    def find_default(self, backgroundorwidget, label_id, default_id):
        # This function finds the id of an items default background or widget

        if label_id is None:
            label_id = default_id

        tree = self.data_func.get_overrides_skin()
        if backgroundorwidget == "background":
            elems = tree.getroot().findall("backgrounddefault")
        elif backgroundorwidget == "widgetdefaultnode":
            elems = tree.getroot().findall("widgetdefaultnode")
        else:
            elems = tree.getroot().findall("widgetdefault")

        if elems is not None:
            for elem in elems:
                if elem.attrib.get("labelID") == label_id or \
                        elem.attrib.get("defaultID") == default_id:
                    if "group" in elem.attrib:
                        if elem.attrib.get("group") == self.group:
                            if backgroundorwidget == "widgetdefaultnode":
                                # if it's a widgetdefaultnode, return the whole element
                                return elem

                            return elem.text

                        continue

                    return elem.text

        return None

    def _set_label(self, listitem, label):
        # Update the label, local string and labelID
        listitem.setLabel(label)
        listitem.setProperty("localizedString", None)

        self.lib_func.rename_playlist(listitem.getProperty("path"), label)

        # If there's no label2, set it to custom shortcut
        if not listitem.getLabel2():
            listitem.setLabel2(LANGUAGE(32024))
            listitem.setProperty("shortcutType", "32024")

    def onAction(self, action):  # pylint: disable=invalid-name
        current_focus = self.getFocusId()
        if action.getId() in ACTION_CANCEL_DIALOG:
            # Close action

            if current_focus and current_focus in self.on_back:
                # Action overridden to return to a control
                self.setFocusId(self.on_back[current_focus])
                return

            # Close window
            self._save_shortcuts()
            xbmcgui.Window(self.window_id).clearProperty('groupname')
            self._close()

        elif current_focus in self.context_controls and action.getId() in ACTION_CONTEXT_MENU:
            # Context menu action
            self._display_context_menu()

        if current_focus == 211:
            # Changed highlighted item, update window properties
            self._add_additional_properties()

    def _display_context_menu(self):
        # Displays a context menu

        context_actions = []
        context_items = []

        # Find active context menu items
        for item in self.context_items:
            # Check any condition
            if item[1] is None or xbmc.getCondVisibility(item[1]):
                # Add the items
                context_actions.append(item[0])
                context_items.append(item[2])

        # Check that there are some items to display
        if len(context_items) == 0:
            log("Context menu called, but no items to display")
            return

        # Display the context menu
        selected_item = xbmcgui.Dialog().contextmenu(list=context_items)

        if selected_item == -1:
            # Nothing selected
            return

        # Call the control associated with the selected item
        self.onClick(context_actions[selected_item])

    def _close(self):
        self.close()

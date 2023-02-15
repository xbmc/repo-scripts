# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import os
import re
import unicodedata
import xml.etree.ElementTree as ETree
from html.entities import name2codepoint
from traceback import print_exc

import xbmc
import xbmcvfs
from unidecode import unidecode

from . import nodefunctions
from .common import log
from .constants import ADDON
from .constants import ADDON_ID
from .constants import DATA_PATH
from .constants import DEFAULT_PATH
from .constants import KODI_VERSION
from .constants import LANGUAGE
from .constants import PROFILE_PATH
from .constants import PROPERTIES_FILE
from .constants import SKIN_DIR
from .constants import SKIN_SHORTCUTS_PATH
from .hash_utils import read_hashes
from .property_utils import read_properties

# character entity reference
CHAR_ENTITY_REXP = re.compile(r'&(%s);' % '|'.join(name2codepoint))
# decimal character reference
DECIMAL_REXP = re.compile(r'&#(\d+);')
# hexadecimal character reference
HEX_REXP = re.compile(r'&#x([\da-fA-F]+);')

REPLACE1_REXP = re.compile(r'[\']+')
REPLACE2_REXP = re.compile(r'[^-a-z0-9]+')
REMOVE_REXP = re.compile(r'-{2,}')


class DataFunctions:
    def __init__(self):
        self.node_func = nodefunctions.NodeFunctions()

        self.overrides = {}

        self.widget_name_and_type = {}
        self.background_name = {}
        self.fallback_properties = {}
        self.fallback_requires = {}
        self.property_requires = None
        self.template_only_properties = None

        self.current_properties = None
        self.default_properties = None

        self.property_information = {
            "fallbackProperties": {},
            "fallbacks": {},
            "otherProperties": [],
            "requires": None,
            "templateOnly": None
        }

        self.label_id_list = []

        self.default_overrides_file = os.path.join(DEFAULT_PATH, "overrides.xml")
        self.skin_overrides_file = os.path.join(SKIN_SHORTCUTS_PATH, "overrides.xml")

        self.hashable = set()
        self.hashable.add(PROPERTIES_FILE)
        self.hashable.add(self.default_overrides_file)
        self.hashable.add(self.skin_overrides_file)

    def get_label_id(self, label_id, action, get_default_id=False,
                     include_addon_id=True, localized_only=False):
        # This gets the unique label_id for the item we've been passed.
        # We'll also store it, to make sure we don't give it to any other item.

        label_id = self.create_nice_name(self.slugify(label_id.replace(" ", "").lower()),
                                         localized_only)

        if include_addon_id:
            addon_label_id = self._get_addon_label_id(action)
            if addon_label_id is not None:
                label_id = addon_label_id

        # If we're getting the defaultID, just return this
        if get_default_id is True:
            return label_id

        # Check if the label_id exists in the list
        if label_id in self.label_id_list:
            # We're going to add an --[int] to the end of this
            count = 0
            id_strtpl = "%s--%s"
            while id_strtpl % (label_id, str(count)) in self.label_id_list:
                count += 1

            # We can now use this one
            self.label_id_list.append(id_strtpl % (label_id, str(count)))
            return id_strtpl % (label_id, str(count))

        # We can use this one
        self.label_id_list.append(label_id)
        return label_id

    @staticmethod
    def _get_addon_label_id(action):
        # This will check the action to see if this is a program or the root of a plugin and,
        # if so, return that as the label_id

        if action is None:
            return None

        try:
            if action.startswith("RunAddOn(") and "," not in action:
                return action[9:-1]

            if action.startswith("RunScript(") and "," not in action:
                return action[10:-1]

            if "plugin://" in action and "?" not in action:
                # Return the action
                # - less ActivateWindow(
                # - The second group after being split by comma
                # - Less plugin://
                return action[15:-1].split(",")[1].replace('"', '')[9:]
        except:
            return None

        return None

    def clear_label_id(self):
        # This clears our stored list of label_id's
        self.label_id_list = []

    def _pop_label_id(self):
        self.label_id_list.pop()

    def get_shortcuts(self, group, default_group=None, profile_dir=None,
                      defaults_only=False, process_shortcuts=True, is_sub_level=False):
        # This will load the shortcut file
        # Additionally, if the override files haven't been loaded, we'll load them too
        log("Loading shortcuts for group %s" % group)

        if profile_dir is None:
            profile_dir = PROFILE_PATH

        user_shortcuts = self.data_xml_filename(os.path.join(profile_dir, "addon_data", ADDON_ID),
                                                self.slugify(group, True,
                                                             is_sub_level=is_sub_level))
        skin_shortcuts = self.data_xml_filename(SKIN_SHORTCUTS_PATH, self.slugify(group))
        default_shortcuts = self.data_xml_filename(DEFAULT_PATH, self.slugify(group))
        if default_group is not None:
            skin_shortcuts = self.data_xml_filename(SKIN_SHORTCUTS_PATH,
                                                    self.slugify(default_group))
            default_shortcuts = self.data_xml_filename(DEFAULT_PATH, self.slugify(default_group))

        if defaults_only:
            paths = [skin_shortcuts, default_shortcuts]
        else:
            paths = [user_shortcuts, skin_shortcuts, default_shortcuts]

        for path in paths:
            self.hashable.add(path)  # add paths to hashable items

        for path in paths:
            log("Attempting to load file %s" % path)
            tree = None

            if xbmcvfs.exists(path):
                try:
                    tree = ETree.parse(path)
                except:
                    log("Failed attempt to load file %s" % path)
                    continue

            if tree is not None and process_shortcuts:
                # If this is a user-selected list of shortcuts...
                if group == "mainmenu":
                    self._get_skin_required(tree)

                if path == user_shortcuts:
                    # Process shortcuts, marked as user-selected
                    self._process_shortcuts(tree, group, profile_dir, True)
                else:
                    self._process_shortcuts(tree, group, profile_dir)

                log("Loaded file")
                return tree

            if tree is not None:
                log("Loaded file %s" % path)
                log("Returning unprocessed shortcuts")
                return tree

        # No file loaded
        log("No shortcuts")
        return ETree.ElementTree(ETree.Element("shortcuts"))

    def _process_shortcuts(self, tree, group, profile_dir="special://profile",
                           is_user_shortcuts=False):
        # This function will process any overrides and add them to the tree ready to be displayed
        #  - We will process graphics overrides, action overrides, visibility conditions
        skinoverrides = self.get_overrides_skin()
        useroverrides = self._get_overrides_user(profile_dir)

        self.clear_label_id()

        # Iterate through all <shortcut/> nodes
        for node in tree.getroot().findall("shortcut"):
            # If not user shortcuts, remove locked nodes (in case of naughty skinners!)
            if is_user_shortcuts is False:
                search_node = node.find("locked")
                if search_node is not None:
                    node.remove(search_node)

            # Remove any labelID node (because it confuses us!)
            search_node = node.find("labelID")
            if search_node is not None:
                node.remove(search_node)

            # Get the action
            action = node.find("action")
            if not action.text:
                action.text = "noop"

            # group overrides: add an additional onclick action for a particular menu
            # this will allow you to close a modal dialog before calling any other window
            # http://forum.kodi.tv/showthread.php?tid=224683
            all_group_overrides = skinoverrides.findall("groupoverride")
            for override in all_group_overrides:
                if override.attrib.get("group") == group:
                    newaction = ETree.SubElement(node, "additional-action")
                    newaction.text = override.text
                    newaction.set("condition", override.attrib.get("condition"))

            # Generate the label_id
            label_id = self.get_label_id(
                self.local(node.find("label").text)[3].replace(" ", "").lower(), action.text
            )
            ETree.SubElement(node, "labelID").text = label_id

            # If there's no defaultID, set it to the labelID
            default_id = label_id
            if node.find("defaultID") is not None:
                default_id = node.find("defaultID").text
            ETree.SubElement(node, "defaultID").text = default_id

            # Check that any version node matches current XBMC version
            version = node.find("version")
            if version is not None:
                if KODI_VERSION != version.text and \
                        self.check_version_equivalency(node.find("action")) is False:
                    tree.getroot().remove(node)
                    self._pop_label_id()
                    continue

            # Get any disabled element
            if node.find("disabled") is not None:
                ETree.SubElement(node, "disabled").text = "True"

            # Load additional properties
            additional_properties = self.check_additional_properties(group, label_id, default_id,
                                                                     is_user_shortcuts)

            # If icon and thumbnail are in the additional properties,
            # overwrite anything in the .DATA.xml file
            # and remove them from the additional properties
            for additional_property in additional_properties.copy():
                if additional_property[0] == "icon":
                    node.find("icon").text = additional_property[1]
                    additional_properties.remove(additional_property)
                    break

            if node.find("thumb") is None:
                ETree.SubElement(node, "thumb").text = ""

            for additional_property in additional_properties.copy():
                if additional_property[0] == "thumb":
                    node.find("thumb").text = additional_property[1]
                    additional_properties.remove(additional_property)
                    break

            ETree.SubElement(node, "additional-properties").text = repr(additional_properties)

            icon_node = node.find("icon")
            if icon_node.text is None or icon_node.text == "":
                icon_node.text = "DefaultShortcut.png"

            # Get a skin-overridden icon
            overridden_icon = self._get_icon_overrides(
                skinoverrides, node.find("icon").text, group, label_id
            )
            if overridden_icon is not None:
                # Add a new node with the overridden icon
                ETree.SubElement(node, "override-icon").text = overridden_icon

            # If the action uses the special://skin protocol, translate it
            if "special://skin/" in action.text:
                action.text = xbmcvfs.translatePath(action.text)

            # Get visibility condition
            visibility_condition = self.check_visibility(action.text)
            visibility_node = None

            if visibility_condition != "":
                # Check whether visibility condition is overridden
                overridden_visibility = False
                for override in skinoverrides.findall("visibleoverride"):
                    if override.attrib.get("condition").lower() != visibility_condition.lower():
                        # Not overriding this visibility condition
                        continue

                    if "group" in override.attrib and not override.attrib.get("group") == group:
                        # Not overriding this group
                        continue

                    overridden_visibility = True

                    # It's overridden - add the original action with the visibility condition
                    original_action = ETree.SubElement(node, "override-visibility")
                    original_action.text = action.text
                    original_action.set("condition", visibility_condition)

                    # And add the new action with the inverse visibility condition
                    newaction = ETree.SubElement(node, "override-visibility")
                    newaction.text = override.text
                    newaction.set("condition", "![%s]" % visibility_condition)

                    break

                if overridden_visibility is False:
                    # The skin hasn't overridden the visibility
                    visibility_node = ETree.SubElement(node, "visibility")
                    visibility_node.text = visibility_condition

            # Get action and visibility overrides
            override_trees = [useroverrides, skinoverrides]
            has_overriden = False
            for override_tree in override_trees:
                if has_overriden is True:
                    continue

                if override_tree is not None:
                    for elem in override_tree.findall("override"):
                        # Pull out the current action, and any already-overridden actions
                        items_to_override = []
                        for item_to_override in node.findall("override-visibility"):
                            items_to_override.append(item_to_override)

                        if len(items_to_override) == 0:
                            items_to_override = [action]

                        # Retrieve group property
                        check_group = None
                        if "group" in elem.attrib:
                            check_group = elem.attrib.get("group")

                        # Iterate through items
                        for item_to_override in items_to_override:
                            # If the action and (if provided) the group match...
                            # OR if we have a global override specified
                            newaction = None

                            if (elem.attrib.get("action") == item_to_override.text and
                                (check_group is None or check_group == group)) or \
                                    (elem.attrib.get("action") == "globaloverride" and
                                     (check_group is None or check_group == group)):

                                # Check the XBMC version matches
                                if "version" in elem.attrib:
                                    if elem.attrib.get("version") != KODI_VERSION:
                                        continue

                                has_overriden = True
                                item_to_override.set("overridden", "True")

                                # Get the visibility condition
                                condition = elem.find("condition")
                                override_visibility = None
                                if condition is not None:
                                    override_visibility = condition.text

                                # Get the new action
                                for actions in elem.findall("action"):
                                    newaction = ETree.SubElement(node, "override-action")
                                    if "::ACTION::" in actions.text:
                                        newaction.text = actions.text.replace("::ACTION::",
                                                                              item_to_override.text)
                                    else:
                                        newaction.text = actions.text

                                    if override_visibility is not None:
                                        newaction.set("condition", override_visibility)

                                # Add visibility if no action specified
                                if len(elem.findall("action")) == 0:
                                    newaction = ETree.SubElement(node, "override-action")
                                    newaction.text = item_to_override.text

                                    if override_visibility is not None:
                                        newaction.set("condition", override_visibility)

                                # If there's already a condition, add it
                                if newaction is not None and item_to_override.get("condition"):
                                    newaction.set("condition", "[%s] + [%s]" %
                                                  (item_to_override.get("condition"),
                                                   newaction.get("condition")))

            # Sort any visibility overrides
            for elem in node.findall("override-visibility"):
                if elem.get("overridden") == "True":
                    # The item has been overridden, delete it
                    node.remove(elem)
                else:
                    # The item hasn't been overridden, so change it to an override-action element
                    elem.tag = "override-action"

            node_strtpl = "[%s] + [%s]"
            # Get visibility condition of any skin-provided shortcuts
            for elem in skinoverrides.findall("shortcut"):
                if elem.text == action.text and "condition" in elem.attrib:
                    if not visibility_node:
                        ETree.SubElement(node, "visibility").text = elem.attrib.get("condition")
                    else:
                        visibility_node.text = \
                            node_strtpl % (visibility_node.text, elem.attrib.get("condition"))

            # Get any visibility conditions in the .DATA.xml file
            additional_visibility = node.find("visible")
            if additional_visibility is not None:
                if visibility_node is None:
                    ETree.SubElement(node, "visibility").text = additional_visibility.text
                else:
                    visibility_node.text = \
                        node_strtpl % (visibility_node.text, additional_visibility.text)

        return tree

    def _get_skin_required(self, listitems):
        # This function builds a tree of any skin-required shortcuts not currently in the menu
        # Once the tree is built, it sends them to _process_shortcuts for any overrides, etc,
        # then adds them to the menu tree

        tree = self.get_overrides_skin()

        # Get an array of all actions currently in the menu
        actions = []
        for node in listitems.getroot().findall("shortcut"):
            for action in node.findall("action"):
                actions.append(action.text)

        # Get a list of all skin-required shortcuts
        for elem in tree.findall("requiredshortcut"):
            if elem.text not in actions:
                # We need to add this shortcut - add it to the listitems
                required_shortcut = ETree.SubElement(listitems.getroot(), "shortcut")

                # Label and label2
                ETree.SubElement(required_shortcut, "label").text = elem.attrib.get("label")
                ETree.SubElement(required_shortcut, "label2").text = SKIN_DIR

                # Icon and thumbnail
                if "icon" in elem.attrib:
                    ETree.SubElement(required_shortcut, "icon").text = elem.attrib.get("icon")
                else:
                    ETree.SubElement(required_shortcut, "icon").text = "DefaultShortcut.png"

                if "thumb" in elem.attrib:
                    ETree.SubElement(required_shortcut, "thumb").text = \
                        elem.attrib.get("thumbnail")

                # Action
                ETree.SubElement(required_shortcut, "action").text = elem.text

                # Locked
                # - This is set to the skin directory, so it will only be locked in the
                # management directory when using this skin
                ETree.SubElement(required_shortcut, "lock").text = SKIN_DIR

    @staticmethod
    def icon_override(tree, icon, group, label_id):
        old_icon = None
        new_icon = icon

        if tree is not None:
            for elem in tree.findall("icon"):
                if old_icon is not None:
                    continue

                if elem.attrib.get("labelID") == label_id or elem.attrib.get("image") == icon:
                    # LabelID matched
                    if "group" in elem.attrib:
                        if elem.attrib.get("group") == group:
                            # Group also matches - change icon
                            old_icon = icon
                            new_icon = elem.text

                    elif "grouping" not in elem.attrib:
                        # No group - change icon
                        old_icon = icon
                        new_icon = elem.text

        return old_icon, new_icon

    def _get_icon_overrides(self, tree, icon, group, label_id, set_to_default=True):
        # This function will get any icon overrides based on label_id or group
        if icon is None:
            return None

        # If the icon is a VAR or an INFO, we aren't going to override
        if icon.startswith("$"):
            return icon

        _, new_icon = self.icon_override(tree, icon, group, label_id)

        if not (xbmc.skinHasImage(new_icon) or xbmcvfs.exists(new_icon)) and set_to_default is True:
            new_icon = self._get_icon_overrides(tree, "DefaultShortcut.png", group, label_id, False)

        return new_icon

    def get_overrides_script(self):
        # Get overrides.xml provided by script
        if "script" in self.overrides:
            return self.overrides["script"]

        try:
            tree = ETree.parse(self.default_overrides_file)
            self.overrides["script"] = tree
            return tree
        except:
            if xbmcvfs.exists(self.default_overrides_file):
                log("Unable to parse script overrides.xml. Invalid xml?")

            tree = ETree.ElementTree(ETree.Element("overrides"))
            self.overrides["script"] = tree
            return tree

    def get_overrides_skin(self):
        # Get overrides.xml provided by skin
        if "skin" in self.overrides:
            return self.overrides["skin"]

        try:
            tree = ETree.parse(self.skin_overrides_file)
            self.overrides["skin"] = tree
            return tree
        except:
            if xbmcvfs.exists(self.skin_overrides_file):
                log("Unable to parse skin overrides.xml. Invalid xml?")

            tree = ETree.ElementTree(ETree.Element("overrides"))
            self.overrides["skin"] = tree
            return tree

    def _get_overrides_user(self, profile_dir="special://profile"):
        # Get overrides.xml provided by user
        if "user" in self.overrides:
            return self.overrides["user"]

        override_path = os.path.join(profile_dir, "overrides.xml")
        self.hashable.add(override_path)
        try:
            tree = ETree.parse(xbmcvfs.translatePath(override_path))
            self.overrides["user"] = tree
            return tree
        except:
            if xbmcvfs.exists(override_path):
                log("Unable to parse user overrides.xml. Invalid xml?")

            tree = ETree.ElementTree(ETree.Element("overrides"))
            self.overrides["user"] = tree
            return tree

    def get_additionalproperties(self):
        # Load all saved properties (widgets, backgrounds, custom properties)

        if self.current_properties is not None:
            return [self.current_properties, self.default_properties]

        self.current_properties = []
        self.default_properties = []

        if xbmcvfs.exists(PROPERTIES_FILE):
            # The properties file exists, load from it
            try:
                list_properties = read_properties()

                for list_property in list_properties:
                    # list_property[0] = groupname
                    # list_property[1] = labelID
                    # list_property[2] = property name
                    # list_property[3] = property value

                    # If list_property[3] starts with $SKIN, it's from an older version of the
                    # script so quickly run it through the local function to remove the
                    # unnecessary localisation
                    if list_property[3].startswith("$SKIN["):
                        list_property[3] = self.local(list_property[3])[3]
                    self.current_properties.append([list_property[0], list_property[1],
                                                    list_property[2], list_property[3]])
            except:
                log(print_exc())
                log("Failed to load current properties")
                self.current_properties = [None]

        else:
            self.current_properties = [None]

        # Load skin defaults (in case we need them...)
        tree = self.get_overrides_skin()
        for elem_search in [["widget", tree.findall("widgetdefault")],
                            ["widget:node", tree.findall("widgetdefaultnode")],
                            ["background", tree.findall("backgrounddefault")],
                            ["custom", tree.findall("propertydefault")]]:
            for elem in elem_search[1]:
                # Get labelID and defaultID
                label_id = elem.attrib.get("labelID")
                default_id = label_id
                if "defaultID" in elem.attrib:
                    default_id = elem.attrib.get("defaultID")

                if elem_search[0] == "custom":
                    # Custom property
                    if "group" not in elem.attrib:
                        self.default_properties.append(["mainmenu", label_id,
                                                        elem.attrib.get('property'),
                                                        elem.text, default_id])
                    else:
                        self.default_properties.append([elem.attrib.get("group"), label_id,
                                                        elem.attrib.get('property'),
                                                        elem.text, default_id])

                else:
                    # Widget or background
                    if "group" not in elem.attrib:
                        self.default_properties.append(["mainmenu", label_id,
                                                        elem_search[0].split(":", maxsplit=1)[0],
                                                        elem.text, default_id])

                        if elem_search[0] == "background":
                            # Get and set the background name
                            background_name = self._get_background_name(elem.text)
                            if background_name is not None:
                                self.default_properties.append(["mainmenu", label_id,
                                                                "backgroundName", background_name,
                                                                default_id])

                        if elem_search[0] == "widget":
                            # Get and set widget type and name
                            widget_details = self._get_widget_name_and_type(elem.text)
                            if widget_details is not None:
                                self.default_properties.append(["mainmenu", label_id, "widgetName",
                                                                widget_details["name"], default_id])
                                if "type" in widget_details:
                                    self.default_properties.append(["mainmenu", label_id,
                                                                    "widgetType",
                                                                    widget_details["type"],
                                                                    default_id])

                                if "path" in widget_details:
                                    self.default_properties.append(["mainmenu", label_id,
                                                                    "widgetPath",
                                                                    widget_details["path"],
                                                                    default_id])

                                if "target" in widget_details:
                                    self.default_properties.append(["mainmenu", label_id,
                                                                    "widgetTarget",
                                                                    widget_details["target"],
                                                                    default_id])

                        if elem_search[0] == "widget:node":
                            # Set all widget properties from the default
                            if elem.text:
                                self.default_properties.append(["mainmenu", label_id, "widget",
                                                                elem.attrib.get("label"),
                                                                default_id])

                            if "label" in elem.attrib:
                                self.default_properties.append(["mainmenu", label_id, "widgetName",
                                                                elem.attrib.get("label"),
                                                                default_id])

                            if "type" in elem.attrib:
                                self.default_properties.append(["mainmenu", label_id, "widgetType",
                                                                elem.attrib.get("type"),
                                                                default_id])

                            if "path" in elem.attrib:
                                self.default_properties.append(["mainmenu", label_id, "widgetPath",
                                                                elem.attrib.get("path"),
                                                                default_id])

                            if "target" in elem.attrib:
                                self.default_properties.append(["mainmenu", label_id,
                                                                "widgetTarget",
                                                                elem.attrib.get("target"),
                                                                default_id])

                    else:
                        self.default_properties.append([elem.attrib.get("group"), label_id,
                                                        elem_search[0].split(":", maxsplit=1)[0],
                                                        elem.text, default_id])

                        if elem_search[0] == "background":
                            # Get and set the background name
                            background_name = self._get_background_name(elem.text)
                            if background_name is not None:
                                self.default_properties.append([elem.attrib.get("group"), label_id,
                                                                "backgroundName", background_name,
                                                                default_id])

                        if elem_search[0] == "widget":
                            # Get and set widget type and name
                            widget_details = self._get_widget_name_and_type(elem.text)
                            if widget_details is not None:
                                self.default_properties.append([elem.attrib.get("group"),
                                                                label_id,
                                                                "widgetName",
                                                                widget_details["name"],
                                                                default_id])

                                if "type" in widget_details:
                                    self.default_properties.append([elem.attrib.get("group"),
                                                                    label_id, "widgetType",
                                                                    widget_details["type"],
                                                                    default_id])

                                if "path" in widget_details:
                                    self.default_properties.append([elem.attrib.get("group"),
                                                                    label_id, "widgetPath",
                                                                    widget_details["path"],
                                                                    default_id])

                                if "target" in widget_details:
                                    self.default_properties.append([elem.attrib.get("group"),
                                                                    label_id, "widgetTarget",
                                                                    widget_details["target"],
                                                                    default_id])

                        if elem_search[0] == "widget:node":
                            # Set all widget properties from the default
                            if "label" in elem.attrib:
                                self.default_properties.append([elem.attrib.get("group"), label_id,
                                                                "widgetName",
                                                                elem.attrib.get("label"),
                                                                default_id])

                            if "type" in elem.attrib:
                                self.default_properties.append([elem.attrib.get("group"), label_id,
                                                                "widgetType",
                                                                elem.attrib.get("type"),
                                                                default_id])

                            if "path" in elem.attrib:
                                self.default_properties.append([elem.attrib.get("group"), label_id,
                                                                "widgetPath",
                                                                elem.attrib.get("path"),
                                                                default_id])

                            if "target" in elem.attrib:
                                self.default_properties.append([elem.attrib.get("group"), label_id,
                                                                "widgetTarget",
                                                                elem.attrib.get("target"),
                                                                default_id])

        # Load icons out of mainmenu.DATA.xml
        path = self.data_xml_filename(SKIN_SHORTCUTS_PATH, "mainmenu")
        self.hashable.add(path)

        if xbmcvfs.exists(path):
            tree = ETree.parse(path)
            for node in tree.getroot().findall("shortcut"):
                label = self.local(node.find("label").text)[3].replace(" ", "").lower()
                action = node.find("action.text")
                label_id = self.get_label_id(label, action, get_default_id=True)
                self.default_properties.append(["mainmenu", label_id, "icon",
                                                node.find("icon").text])

        return_val = [self.current_properties, self.default_properties]
        return return_val

    def get_custom_property_fallbacks(self, group):
        if group in self.property_information["fallbacks"]:
            # We've already loaded everything, return it all
            return self.property_information["fallbackProperties"][group], \
                   self.property_information["fallbacks"][group]

        # Get skin overrides
        tree = self.get_overrides_skin()

        # Find all fallbacks
        fallback_properties = []
        fallbacks = {}
        for elem in tree.findall("propertyfallback"):
            if ("group" not in elem.attrib and group == "mainmenu") or \
                    elem.attrib.get("group") == group:
                # This is a fallback for the group we've been asked for
                property_name = elem.attrib.get("property")
                if property_name not in fallback_properties:
                    # Save the property name in the order in which we processed it
                    fallback_properties.append(property_name)

                if property_name not in fallbacks:
                    # Create an empty list to hold fallbacks for this property
                    fallbacks[property_name] = []

                # Check whether any attribute/value pair has to match for this fallback
                attrib_name = None
                attrib_value = None
                if "attribute" in elem.attrib and "value" in elem.attrib:
                    # This particular property is a matched property
                    attrib_name = elem.attrib.get("attribute")
                    attrib_value = elem.attrib.get("value")

                # Upgrade widgetTarget where value is video to videos
                value = elem.text
                if property_name.startswith("widgetTarget") and value == "video":
                    value = "videos"
                # Save details
                fallbacks[property_name].append((value, attrib_name, attrib_value))
        # Save all the results for this group
        self.property_information["fallbackProperties"][group] = fallback_properties
        self.property_information["fallbacks"][group] = fallbacks

        return \
            self.property_information["fallbackProperties"][group], \
            self.property_information["fallbacks"][group]

    def get_property_requires(self):
        if self.property_information["requires"] is not None:
            # We've already loaded requires and templateOnly properties, return eveything
            return self.property_information["otherProperties"], \
                   self.property_information["requires"], self.property_information["templateOnly"]

        # Get skin overrides
        tree = self.get_overrides_skin()

        # Find all property requirements
        requires = {}
        template_only = []
        for elem in tree.findall("propertySettings"):
            property_name = elem.attrib.get("property")
            if property_name not in self.property_information["otherProperties"]:
                # Save the property name in the order in which we processed it
                self.property_information["otherProperties"].append(property_name)

            if "requires" in elem.attrib:
                # This property requires another to be present
                requires[property_name] = elem.attrib.get("requires")

            if "templateonly" in elem.attrib and elem.attrib.get("templateonly").lower() == "true":
                # This property is only used by the template, and should not be
                # written to the main menu
                template_only.append(property_name)
        # Save all the results
        self.property_information["requires"] = requires
        self.property_information["templateOnly"] = template_only

        return \
            self.property_information["otherProperties"], \
            self.property_information["requires"], \
            self.property_information["templateOnly"]

    def _get_widget_name_and_type(self, widget_id):
        if widget_id in self.widget_name_and_type:
            return self.widget_name_and_type[widget_id]

        tree = self.get_overrides_skin()
        for elem in tree.findall("widget"):
            if elem.text == widget_id:
                widget_info = {
                    "name": elem.attrib.get("label")
                }

                if "type" in elem.attrib:
                    widget_info["type"] = elem.attrib.get("type")

                if "path" in elem.attrib:
                    widget_info["path"] = elem.attrib.get("path")

                if "target" in elem.attrib:
                    widget_info["target"] = elem.attrib.get("target")

                self.widget_name_and_type[widget_id] = widget_info
                return widget_info

        self.widget_name_and_type[widget_id] = None
        return None

    def _get_background_name(self, background_id):
        if background_id in self.background_name:
            return self.background_name[background_id]

        tree = self.get_overrides_skin()
        for elem in tree.findall("background"):
            if elem.text == background_id:
                return_string = elem.attrib.get("label")
                self.background_name[background_id] = return_string
                return return_string

        self.background_name[background_id] = None
        return None

    def reset_backgroundandwidgets(self):
        # This function resets all skin properties used to identify if specific backgrounds or
        # widgets are active
        tree = self.get_overrides_skin()
        for elem in tree.findall("widget"):
            xbmc.executebuiltin("Skin.Reset(skinshortcuts-widget-%s)" % elem.text)

        for elem in tree.findall("background"):
            xbmc.executebuiltin("Skin.Reset(skinshortcuts-background-%s)" % elem.text)

    @staticmethod
    def create_nice_name(item, localized_only=False):
        # Translate certain localized strings into non-localized form for labelID
        default = item.lower().replace(" ", "")

        if localized_only:
            return default

        strings = {
            '3': 'videos',
            '2': 'music',
            '342': 'movies',
            '20343': 'tvshows',
            '32022': 'livetv',
            '20389': 'musicvideos',
            '10002': 'pictures',
            '12600': 'weather',
            '10001': 'programs',
            '32032': 'dvd',
            '10004': 'settings',
            '32087': 'radio',
        }

        return strings.get(item, default)

    def check_visibility(self, action):
        # Return whether mainmenu items should be displayed
        action = action.lower().replace(" ", "").replace("\"", "")

        # Catch-all for shortcuts to plugins
        if "plugin://" in action:
            return ""

        # Video node visibility
        if action.startswith(("activatewindow(videos,videodb://",
                              "activatewindow(videolibrary,videodb://",
                              "activatewindow(10025,videodb://",
                              "activatewindow(videos,library://video/",
                              "activatewindow(videolibrary,library://video",
                              "activatewindow(10025,library://video/")):
            path = action.split(",")
            if path[1].endswith(")"):
                path[1] = path[1][:-1]

            return self.node_func.get_visibility(path[1])

        # Audio node visibility - Isengard and earlier
        if action.startswith("activatewindow(musiclibrary,musicdb://") or \
                action.startswith("activatewindow(10502,musicdb://") or \
                action.startswith("activatewindow(musiclibrary,library://music/") or \
                action.startswith("activatewindow(10502,library://music/"):
            path = action.split(",")
            if path[1].endswith(")"):
                path[1] = path[1][:-1]

            return self.node_func.get_visibility(path[1])

        # Audio node visibility - Additional checks for Jarvis and later
        # (Note when cleaning up in the future, some of the Isengard checks -
        # those with window 10502 - are still valid...)
        if action.startswith("activatewindow(music,musicdb://") or \
                action.startswith("activatewindow(music,library://music/"):
            path = action.split(",")
            if path[1].endswith(")"):
                path[1] = path[1][:-1]

            return self.node_func.get_visibility(path[1])

        # Power menu visibilities
        if action in ("quit()", "quit"):
            return "System.ShowExitButton"

        if action in ("powerdown()", "powerdown"):
            return "System.CanPowerDown"

        if action == "alarmclock(shutdowntimer,shutdown())":
            return "!System.HasAlarm(shutdowntimer) + [System.CanPowerDown | System.CanSuspend " \
                   "| System.CanHibernate]"

        if action == "cancelalarm(shutdowntimer)":
            return "System.HasAlarm(shutdowntimer)"

        if action in ("suspend()", "suspend"):
            return "System.CanSuspend"

        if action in ("hibernate()", "hibernate"):
            return "System.CanHibernate"

        if action in ("reset()", "reset"):
            return "System.CanReboot"

        if action == "system.logoff":
            return "[System.HasLoginScreen | Integer.IsGreater(System.ProfileCount,1)] + " \
                   "System.Loggedon"

        if action == "mastermode":
            return "System.HasLocks"

        if action == "inhibitidleshutdown(true)":
            return "System.HasShutdown +!System.IsInhibit"

        if action == "inhibitidleshutdown(false)":
            return "System.HasShutdown + System.IsInhibit"

        if action == "restartapp":
            return "[System.Platform.Windows | System.Platform.Linux] +! " \
                   "System.Platform.Linux.RaspberryPi"

        # General visibilities
        if action == "activatewindow(weather)":
            return "!String.IsEmpty(Weather.Plugin)"

        if action.startswith("activatewindowandfocus(mypvr") or action.startswith("playpvr") and \
                not ADDON.getSettingBool("donthidepvr"):
            return "PVR.HasTVChannels"

        if action.startswith("activatewindow(tv") and not ADDON.getSettingBool("donthidepvr"):
            return "System.HasPVRAddon"

        if action.startswith("activatewindow(radio") and \
                not ADDON.getSettingBool("donthidepvr"):
            return "System.HasPVRAddon"

        if action.startswith("activatewindow(videos,movie"):
            return "Library.HasContent(Movies)"

        if action.startswith("activatewindow(videos,recentlyaddedmovies"):
            return "Library.HasContent(Movies)"

        if action.startswith("activatewindow(videos,tvshow") or \
                action.startswith("activatewindow(videos,tvshow"):
            return "Library.HasContent(TVShows)"

        if action.startswith("activatewindow(videos,recentlyaddedepisodes"):
            return "Library.HasContent(TVShows)"

        if action.startswith("activatewindow(videos,musicvideo"):
            return "Library.HasContent(MusicVideos)"

        if action.startswith("activatewindow(videos,recentlyaddedmusicvideos"):
            return "Library.HasContent(MusicVideos)"

        if action in ("xbmc.playdvd()", "playdvd"):
            return "System.HasMediaDVD"

        if action.startswith("activatewindow(eventlog"):
            return "system.getbool(eventlog.enabled)"

        return ""

    def check_version_equivalency(self, action, check_type="shortcuts"):
        # Check whether the version specified for a shortcut has an equivalency
        # to the version of Kodi we're running
        trees = [self.get_overrides_skin(), self.get_overrides_script()]

        # Set up so we can handle both groupings and shortcuts in one
        find_elem = ""
        find_attrib = ""
        if check_type == "shortcuts":
            if action is None:
                action = ""
            else:
                action = action.text

            find_elem = "shortcutEquivalent"
            find_attrib = "action"

        elif check_type == "groupings":
            if action is None:
                action = ""
            find_elem = "groupEquivalent"
            find_attrib = "condition"

        if not find_elem or not find_attrib:
            return False

        for tree in trees:
            if tree.find("versionEquivalency") is None:
                continue

            for elem in tree.find("versionEquivalency").findall(find_elem):
                if elem.attrib.get(find_attrib) is not None and \
                        elem.attrib.get(find_attrib).lower() != action.lower():
                    # Action's don't match
                    continue
                if int(elem.attrib.get("version")) > int(KODI_VERSION):
                    # This version of Kodi is older than the shortcut is intended for
                    continue

                # The actions match, and the version isn't too old, so
                # now check it's not too new
                if elem.text == "All":
                    # This shortcut matches all newer versions
                    return True

                if int(elem.text) >= int(KODI_VERSION):
                    return True

                # The version didn't match
                break

        return False

    def check_additional_properties(self, group, label_id, default_id, is_user_shortcuts):
        # Return any additional properties, including widgets, backgrounds, icons and thumbnails
        all_properties = self.get_additionalproperties()
        current_properties = all_properties[1]

        return_properties = []

        # This returns two lists...
        #  all_properties[0] = Saved properties
        #  all_properties[1] = Default properties

        if is_user_shortcuts and (len(all_properties[0]) == 0 or all_properties[0][0] is not None):
            current_properties = all_properties[0]

        # Loop through the current properties, looking for the current item
        # pylint: disable=unsubscriptable-object
        for current_property in current_properties:
            # current_property[0] = Group name
            # current_property[1] = labelID
            # current_property[2] = Property name
            # current_property[3] = Property value
            # current_property[4] = defaultID
            if label_id is not None and current_property[0] == group and \
                    current_property[1] == label_id:
                return_properties.append(
                    self.upgrade_additional_properties(current_property[2], current_property[3])
                )

            elif len(current_property) != 4:
                if default_id is not None and current_property[0] == group and \
                        current_property[4] == default_id:
                    return_properties.append(
                        self.upgrade_additional_properties(current_property[2], current_property[3])
                    )

        return return_properties

    def check_shortcut_label_override(self, action):
        tree = self.get_overrides_skin()
        if tree is not None:
            elem_search = tree.findall("availableshortcutlabel")
            for elem in elem_search:
                if elem.attrib.get("action").lower() == action.lower():
                    # This matches :) Check if we're also overriding the type
                    if "type" in elem.attrib:
                        return [elem.text, elem.attrib.get("type")]

                    return [elem.text]

        return None

    def check_if_menus_shared(self, is_sub_level=False):
        # Check if the skin required the menu not to be shared
        tree = self.get_overrides_skin()
        if tree is not None:
            # If this is a sublevel, and the skin has asked for sub levels to not be shared...
            if is_sub_level and tree.find("doNotShareLevels") is not None:
                return False

            # If the skin has asked for all menu's not to be shared...
            if tree.find("doNotShareMenu") is not None:
                return False

        # Check if the user has asked for their menus not to be shared
        if not ADDON.getSettingBool("shared_menu"):
            return False

        return True

    def get_shared_skin_list(self):
        # This will return a list of skins the user can import the menu from
        skin_names = []
        skin_files = []
        for files in xbmcvfs.listdir(DATA_PATH):
            # Try deleting all shortcuts
            if files:
                for file in files:
                    if file.endswith(".hash") and not file.startswith("%s-" % SKIN_DIR):
                        can_import, skin_name = self.parse_hash_file(os.path.join(DATA_PATH, file))
                        if can_import is True:
                            skin_names.append(skin_name)

                    elif file.endswith(".DATA.xml") and \
                            not file.startswith("%s-" % SKIN_DIR):
                        skin_files.append(file)

        # Remove any files which start with one of the skin names
        remove_skins = []
        remove_files = []
        for skin_name in skin_names:
            matched = False
            for skin_file in skin_files:
                if skin_file.startswith("%s-" % skin_name):
                    if matched is False:
                        matched = True
                    remove_files.append(skin_file)

            if matched is False:
                # This skin doesn't have a custom menu
                remove_skins.append(skin_name)

        skin_names = [x for x in skin_names if x not in remove_skins]
        skin_files = [x for x in skin_files if x not in remove_files]

        # If there are any files left in skin_files, we have a shared menu
        if len(skin_files) != 0:
            skin_names.insert(0, LANGUAGE(32111))

        return skin_names, skin_files

    @staticmethod
    def get_files_for_skin(skin_name):
        # This will return a list of all menu files for a particular skin
        skin_files = []
        for files in xbmcvfs.listdir(DATA_PATH):
            # Try deleting all shortcuts
            if files:
                for file in files:
                    if file.endswith(".DATA.xml") and file.startswith("%s-" % skin_name):
                        skin_files.append(file)

        return skin_files

    @staticmethod
    def parse_hash_file(hash_file):
        can_import = False
        skin_name = ""

        hashes = read_hashes(hash_file)

        for _hash in hashes:
            if _hash[0] == "::FULLMENU::":
                can_import = True
                if skin_name:
                    return True, skin_name

            if _hash[0] == "::SKINDIR::":
                skin_name = _hash[1]
                if can_import is True:
                    return True, skin_name

        return can_import, skin_name

    @staticmethod
    def import_skin_menu(files, skin_name=None):
        # This function copies one skins menus to another
        for old_file in files:
            if skin_name:
                new_file = old_file.replace(skin_name, SKIN_DIR)
            else:
                new_file = "%s-%s" % (SKIN_DIR, old_file)

            old_path = os.path.join(DATA_PATH, old_file)
            new_path = os.path.join(DATA_PATH, new_file)

            # Copy file
            xbmcvfs.copy(old_path, new_path)

        # Delete any .properties file
        if xbmcvfs.exists(PROPERTIES_FILE):
            xbmcvfs.delete(PROPERTIES_FILE)

    # in-place prettyprint formatter
    def indent(self, elem, level=0):
        whitespace = "\n%s" % (level * "\t")
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = "%s%s" % (whitespace, "\t")

            if not elem.tail or not elem.tail.strip():
                elem.tail = whitespace

            for _elem in elem:
                self.indent(_elem, level + 1)

            if not elem.tail or not elem.tail.strip():
                elem.tail = whitespace

        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = whitespace

    @staticmethod
    def local(data):
        # This is our function to manage localisation
        # It accepts strings in one of the following formats:
        #   #####, ::LOCAL::#####, ::SCRIPT::#####
        #   $LOCALISE[#####], $SKIN[####|skin.id|last translation]
        #   $ADDON[script.skinshortcuts #####]
        # If returns a list containing:
        #   [Number/$SKIN, $LOCALIZE/$ADDON/Local string, Local string]
        #   [Used for saving, used for building xml, used for displaying in dialog]

        if data is None:
            return ["", "", "", ""]

        skinid = None
        lasttranslation = None

        # Get just the integer of the string, for the input forms where this is valid

        if not data.find("::SCRIPT::") == -1:
            data = data[10:]

        elif not data.find("::LOCAL::") == -1:
            data = data[9:]

        elif not data.find("$LOCALIZE[") == -1:
            data = data.replace("$LOCALIZE[", "").replace("]", "").replace(" ", "")

        elif not data.find("$ADDON[script.skinshortcuts") == -1:
            data = data.replace("$ADDON[script.skinshortcuts", "").replace("]", "").replace(" ", "")

        # Get the integer and skin id, from $SKIN input forms
        elif not data.find("$SKIN[") == -1:
            splitdata = data[6:-1].split("|")
            data = splitdata[0]
            skinid = splitdata[1]
            lasttranslation = splitdata[2]

        if data.isdigit():
            if 31000 <= int(data) < 32000:
                # A number from a skin - we're going to return a
                # $SKIN[#####|skin.id|last translation] unit
                if skinid is None:
                    # Set the skinid to the current skin id
                    skinid = SKIN_DIR

                return_string = "$SKIN[%s|%s|%s]" % (data, skinid, lasttranslation)
                # If we're on the same skin as the skinid, get the latest translation
                if skinid == SKIN_DIR:
                    lasttranslation = xbmc.getLocalizedString(int(data))
                    return [return_string, "$LOCALIZE[%s]" % data, lasttranslation, data]

                return [return_string, lasttranslation, lasttranslation, data]

            if 32000 <= int(data) < 33000:
                # A number from the script
                return [data, "$ADDON[script.skinshortcuts %s]" % data,
                        LANGUAGE(int(data)), data]

            # A number from XBMC itself (probably)
            return [data, "$LOCALIZE[%s]" % data, xbmc.getLocalizedString(int(data)), data]

        # This isn't anything we can localize, just return it (in triplicate ;))
        return [data, data, data, data]

    @staticmethod
    def smart_truncate(string, max_length=0, word_boundaries=False, separator=' '):
        string = string.strip(separator)

        if not max_length:
            return string

        if len(string) < max_length:
            return string

        if not word_boundaries:
            return string[:max_length].strip(separator)

        if separator not in string:
            return string[:max_length]

        truncated = ''
        for word in string.split(separator):
            if word:
                next_len = len(truncated) + len(word) + len(separator)
                if next_len <= max_length:
                    truncated += '{0}{1}'.format(word, separator)

        if not truncated:
            truncated = string[:max_length]

        return truncated.strip(separator)

    def slugify(self, text, user_shortcuts=False, entities=True, decimal=True,
                hexadecimal=True, max_length=0, word_boundary=False, separator='-',
                convert_int=False, is_sub_level=False):
        # Handle integers
        if convert_int and text.isdigit():
            text = "NUM-%s" % text

        # text to unicode
        if isinstance(text, bytes):
            text = str(text, 'utf-8', 'ignore')

        # decode unicode ( ??? = Ying Shi Ma)
        text = unidecode(text)

        # character entity reference
        if entities:
            text = CHAR_ENTITY_REXP.sub(lambda m: chr(name2codepoint[m.group(1)]), text)

        # decimal character reference
        if decimal:
            try:
                text = DECIMAL_REXP.sub(lambda m: chr(int(m.group(1))), text)
            except:
                pass

        # hexadecimal character reference
        if hexadecimal:
            try:
                text = HEX_REXP.sub(lambda m: chr(int(m.group(1), 16)), text)
            except:
                pass

        # translate
        text = unicodedata.normalize('NFKD', text)

        # replace unwanted characters
        text = REPLACE1_REXP.sub('', text.lower())  # replace ' with nothing instead with -
        text = REPLACE2_REXP.sub('-', text.lower())

        # remove redundant -
        text = REMOVE_REXP.sub('-', text).strip('-')

        # smart truncate if requested
        if max_length > 0:
            text = self.smart_truncate(text, max_length, word_boundary, '-')

        if separator != '-':
            text = text.replace('-', separator)

        # If this is a shortcut file (.DATA.xml) and user shortcuts aren't shared, add the skin dir
        if user_shortcuts is True and self.check_if_menus_shared(is_sub_level) is False:
            text = "%s-%s" % (SKIN_DIR, text)

        return text

    # ----------------------------------------------------------------
    # --- Functions that should get their own module in the future ---
    # --- (when xml building functions are revamped/simplified) ------
    # ----------------------------------------------------------------

    @staticmethod
    def get_list_property(onclick):
        # For ActivateWindow elements, extract the path property
        if onclick.startswith("ActivateWindow"):
            # An ActivateWindow - Let's start by removing the 'ActivateWindow(' and the ')'
            list_property = onclick
            # Handle (the not uncommon) situation where the trailing ')' has been forgotten
            if onclick.endswith(")"):
                list_property = onclick[:-1]

            list_property = list_property.split("(", 1)[1]

            # Split what we've got left on commas
            list_property = list_property.split(",")

            # Get the part of the onclick that we're actually interested in
            if len(list_property) == 1:
                # 'elementWeWant'
                return list_property[0]

            if len(list_property) == 2 and list_property[1].lower().replace(" ", "") == "return":
                # 'elementWeWant' 'return'
                return list_property[0]

            if len(list_property) == 2:
                # 'windowToActivate' 'elementWeWant'
                return list_property[1]

            if len(list_property) == 3:
                # 'windowToActivate' 'elementWeWant' 'return'
                return list_property[1]

            # Situation we haven't anticipated - log the issue and return original onclick
            log("Unable to get 'list' property for shortcut %s" % onclick)
            return onclick

        # Not an 'ActivateWindow' - return the onclick
        return onclick

    @staticmethod
    def upgrade_action(action):
        # This function looks for actions used in a previous version of Kodi,
        # and upgrades them to the current action

        if not action.lower().startswith("activatewindow("):
            return action

        # Jarvis + later music windows
        if action.lower() == "activatewindow(musicfiles)":
            return "ActivateWindow(Music,Files,Return)"

        if action.lower().startswith("activatewindow(musiclibrary"):
            if "," in action:
                return "ActivateWindow(Music,%s" % action.split(",", 1)[1]

            return "ActivateWindow(Music)"

        # Isengard + later video windows
        if action.lower().startswith("activatewindow(videolibrary"):
            if "," in action:
                return "ActivateWindow(Videos,%s" % action.split(",", 1)[1]

            return "ActivateWindow(Videos)"

        # No matching upgrade
        return action

    @staticmethod
    def upgrade_additional_properties(property_name, property_value):
        # This function fixes any changes to additional properties between Kodi versions
        if property_name.startswith("widgetTarget") and property_value == "video":
            property_value = "videos"

        return [property_name, property_value]

    @staticmethod
    def build_replacement_music_addon_action(action, window):
        # Builds a replacement action for an Isengard or earlier shortcut to a specific music addon
        split_action = action.split(",")
        # [0] = ActivateWindow([window]
        # [1] = "plugin://plugin.name/path?params"
        # [2] = return)

        if len(split_action) == 2:
            return "ActivateWindow(%s,%s)" % (window, split_action[1])

        return "ActivateWindow(%s,%s,return)" % (window, split_action[1])

    @staticmethod
    def data_xml_filename(path, group):
        return os.path.join(path, "%s.DATA.xml" % group)

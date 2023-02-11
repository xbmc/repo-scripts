# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""
import os
import xml.etree.ElementTree as ETree
from traceback import print_exc

import xbmc
import xbmcgui
import xbmcvfs

from . import jsonrpc
from .common import log
from .common_utils import ShowDialog
from .constants import ADDON_NAME
from .constants import CWD
from .constants import DATA_PATH
from .constants import HOME_WINDOW
from .constants import KODI_PATH
from .constants import LANGUAGE
from .constants import PROFILE_PATH
from .property_utils import write_properties


class NodeFunctions:
    def __init__(self):
        self.index_counter = 0

    ##############################################
    # Functions used by library.py to list nodes #
    ##############################################

    def get_nodes(self, path, prefix):
        dirs, files = xbmcvfs.listdir(path)
        nodes = {}

        try:
            for _dir in dirs:
                self.parse_node(os.path.join(path, _dir), _dir, nodes, prefix)

            for file in files:
                self.parse_view(os.path.join(path, file), nodes,
                                orig_path="%s/%s" % (prefix, file))
        except:
            log(print_exc())
            return False

        return nodes

    def parse_node(self, node, directory, nodes, prefix):
        # If the folder we've been passed contains an index.xml, send that file to be processed
        if xbmcvfs.exists(os.path.join(node, "index.xml")):
            self.parse_view(os.path.join(node, "index.xml"), nodes, True,
                            "%s/%s/" % (prefix, directory), node)

    def parse_view(self, file, nodes, is_folder=False, orig_folder=None, orig_path=None):
        if not is_folder and file.endswith("index.xml"):
            return

        try:
            # Load the xml file
            with open(file.encode('utf-8'), "rb") as infile:
                filedata = infile.read().decode('utf-8')

            root = ETree.fromstring(filedata)

            # Get the item index
            if "order" in root.attrib:
                index = root.attrib.get("order")
                orig_index = index
                while int(index) in nodes:
                    index = int(index)
                    index += 1
                    index = str(index)

            else:
                self.index_counter -= 1
                index = str(self.index_counter)
                orig_index = "-"

            # Try to get media type from visibility condition
            media_type = None
            if "visible" in root.attrib:
                visible_attrib = root.attrib.get("visible")
                if not xbmc.getCondVisibility(visible_attrib):
                    # The node isn't visible
                    return

                if "Library.HasContent(" in visible_attrib and "+" not in visible_attrib and \
                        "|" not in visible_attrib:
                    media_type = visible_attrib.split("(")[1].split(")")[0].lower()

            # Try to get media type from content node
            content_node = root.find("content")
            if content_node is not None:
                media_type = content_node.text

            # Get label and icon
            label = root.find("label").text

            icon = root.find("icon")
            if icon is not None:
                icon = icon.text
            else:
                icon = ""

            if is_folder:
                # Add it to our list of nodes
                nodes[int(index)] = [label, icon, orig_folder, "folder", orig_index, media_type]

            else:
                # Check for a path
                path = root.find("path")
                if path is not None:
                    # Change the orig_path (the url used as the shortcut address) to it
                    orig_path = path.text

                # Check for a grouping
                group = root.find("group")
                if group is None:
                    # Add it as an item
                    nodes[int(index)] = [label, icon, orig_path, "item", orig_index, media_type]

                else:
                    # Add it as grouped
                    nodes[int(index)] = [label, icon, orig_path, "grouped", orig_index, media_type]
        except:
            log(print_exc())

    @staticmethod
    def is_grouped(path):
        custom_path_video = path.replace(
            "library://video",
            os.path.join(PROFILE_PATH, "library", "video")
        )[:-1]

        default_path_video = path.replace(
            "library://video",
            os.path.join(KODI_PATH, "system", "library", "video")
        )[:-1]

        custom_path_audio = path.replace(
            "library://music",
            os.path.join(PROFILE_PATH, "library", "music")
        )[:-1]

        default_path_audio = path.replace(
            "library://music",
            os.path.join(KODI_PATH, "system", "library", "music")
        )[:-1]

        paths = [custom_path_video, default_path_video, custom_path_audio, default_path_audio]
        found_path = False

        for try_path in paths:
            if xbmcvfs.exists(try_path):
                path = try_path
                found_path = True
                break

        if found_path is False:
            return False

        # Open the file
        try:
            # Load the xml file
            tree = ETree.parse(path)
            root = tree.getroot()

            group = root.find("group")
            return group is not None

        except:
            return False

    #####################################
    # Function used by DataFunctions.py #
    #####################################

    def get_visibility(self, path):
        path, path_start, path_end = self._modify_path_and_parts(path)

        if None in (path_start, path_end):
            return ""

        custom_path = "%sindex.xml" % path.replace(path_start,
                                                   os.path.join(PROFILE_PATH, "library", path_end))
        custom_file = "%s.xml" % path.replace(path_start,
                                              os.path.join(PROFILE_PATH, "library", path_end))[:-1]
        default_path = \
            "%sindex.xml" % path.replace(path_start,
                                         os.path.join(KODI_PATH, "system", "library", path_end))
        default_file = \
            "%s.xml" % path.replace(path_start,
                                    os.path.join(KODI_PATH, "system", "library", path_end))[:-1]

        # Check whether the node exists - either as a parent node (with an index.xml)
        # or a view node (append .xml) in first custom video nodes, then default video nodes
        node_file = None
        if xbmcvfs.exists(custom_path):
            node_file = custom_path
        elif xbmcvfs.exists(default_path):
            node_file = default_path

        if xbmcvfs.exists(custom_file):
            node_file = custom_file
        elif xbmcvfs.exists(default_file):
            node_file = default_file

        # Next check if there is a parent node
        if path.endswith("/"):
            path = path[:-1]

        path = path.rsplit("/", 1)[0]

        custom_path = "%s/index.xml" % path.replace(path_start,
                                                    os.path.join(PROFILE_PATH, "library", path_end))
        default_path = \
            "%s/index.xml" % path.replace(path_start,
                                          os.path.join(KODI_PATH, "system", "library", path_end))
        node_parent = None

        if xbmcvfs.exists(custom_path):
            node_parent = custom_path
        elif xbmcvfs.exists(default_path):
            node_parent = default_path

        if not node_file and not node_parent:
            return ""

        for xml_file in (node_file, node_parent):
            if xml_file is None:
                continue

            # Open the file
            try:
                # Load the xml file
                tree = ETree.parse(xml_file)
                root = tree.getroot()

                if "visible" in root.attrib:
                    return root.attrib.get("visible")

            except:
                pass

        return ""

    def get_media_type(self, path):
        path, path_start, path_end = self._modify_path_and_parts(path)

        if None in (path_start, path_end):
            return "unknown"

        custom_path = "%sindex.xml" % path.replace(path_start,
                                                   os.path.join(PROFILE_PATH, "library", path_end))
        custom_file = "%s.xml" % path.replace(path_start,
                                              os.path.join(PROFILE_PATH, "library", path_end))[:-1]
        default_path = \
            "%sindex.xml" % path.replace(path_start,
                                         os.path.join(KODI_PATH, "system", "library", path_end))
        default_file = \
            "%s.xml" % path.replace(path_start,
                                    os.path.join(KODI_PATH, "system", "library", path_end))[:-1]

        # Check whether the node exists - either as a parent node (with an index.xml)
        # or a view node (append .xml) in first custom video nodes, then default video nodes
        if xbmcvfs.exists(custom_path):
            path = custom_path

        elif xbmcvfs.exists(custom_file):
            path = custom_file

        elif xbmcvfs.exists(default_path):
            path = default_path

        elif xbmcvfs.exists(default_file):
            path = default_file

        else:
            return "unknown"

        # Open the file
        try:
            # Load the xml file
            tree = ETree.parse(path)
            root = tree.getroot()

            media_type = "unknown"
            if "visible" in root.attrib:
                visible_attrib = root.attrib.get("visible")
                if "Library.HasContent(" in visible_attrib and "+" not in visible_attrib and \
                        "|" not in visible_attrib:
                    media_type = visible_attrib.split("(")[1].split(")")[0].lower()

            content_node = root.find("content")
            if content_node is not None:
                media_type = content_node.text

            return media_type

        except:
            return "unknown"

    ##################################################
    # Functions to externally add a node to the menu #
    ##################################################

    def add_to_menu(self, path, label, icon, content, window, data_func):
        log(repr(window))
        log(repr(label))
        log(repr(path))
        log(repr(content))
        # Show a waiting dialog
        dialog = xbmcgui.DialogProgress()
        dialog.create(path, LANGUAGE(32063))

        # Work out if it's a single item, or a node
        is_node = False
        node_paths = []
        json_path = path.replace("\\", "\\\\")
        json_response = jsonrpc.files_get_directory(json_path, ["title", "file", "thumbnail"])

        # Add all directories returned by the json query
        if json_response:
            labels = [LANGUAGE(32058)]
            paths = ["ActivateWindow(%s,%s,return)" % (window, path)]
            for item in json_response['result']['files']:
                if item["filetype"] == "directory":
                    is_node = True
                    labels.append(item["label"])
                    node_paths.append("ActivateWindow(%s,%s,return)" % (window, item["file"]))

        else:
            # Unable to add to get directory listings
            log("Invalid JSON response returned")
            log(repr(json_response))
            # And tell the user it failed
            xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(32115))
            return

        # Add actions based on content
        if content == "albums":
            labels.append("Play")
            paths.append("RunScript(script.skinshortcuts,type=launchalbum&album=%s)" %
                         (self.extract_id(path)))

        if window == 10002:
            labels.append("Slideshow")
            paths.append("SlideShow(%s,notrandom)" % path)
            labels.append("Slideshow(random)")
            paths.append("SlideShow(%s,random)" % path)
            labels.append("Slideshow(recursive)")
            paths.append("SlideShow(%s,recursive,notrandom)" % path)
            labels.append("Slideshow(recursive,random)")
            paths.append("SlideShow(%s,recursive,random)" % path)

        if path.endswith(".xsp"):
            labels.append("Play")
            paths.append("PlayMedia(%s)" % path)

        all_menu_items = [xbmcgui.ListItem(label=LANGUAGE(32112), offscreen=True)]  # Main menu
        all_label_ids = ["mainmenu"]
        if is_node:
            # Main menu + autofill submenu
            all_menu_items.append(
                xbmcgui.ListItem(label=LANGUAGE(32113, offscreen=True))
            )
            all_label_ids.append("mainmenu")

        # Get main menu items
        menuitems = data_func.get_shortcuts("mainmenu", processShortcuts=False)
        data_func.clear_label_id()
        for menuitem in menuitems.findall("shortcut"):
            # Get existing items labelID's
            listitem = xbmcgui.ListItem(label=data_func.local(menuitem.find("label").text)[2],
                                        offscreen=True)
            listitem.setArt({
                'icon': menuitem.find("icon").text
            })
            all_menu_items.append(listitem)
            all_label_ids.append(data_func.get_label_id(
                data_func.local(menuitem.find("label").text)[3], menuitem.find("action").text)
            )

        # Close progress dialog
        dialog.close()

        # Show a select dialog so the user can pick where in the menu to add the item
        show_dialog = ShowDialog(
            "DialogSelect.xml", CWD, listing=all_menu_items, window_title=LANGUAGE(32114)
        )
        show_dialog.doModal()
        selected_menu = show_dialog.result
        del show_dialog

        if selected_menu == -1 or selected_menu is None:
            # User cancelled
            return

        action = paths[0]
        if is_node and selected_menu == 1:
            # We're auto-filling submenu, so add all sub-nodes as possible default actions
            paths = paths + node_paths

        if len(paths) > 1:
            # There are multiple actions to choose from
            selected_action = xbmcgui.Dialog().select(LANGUAGE(32095), labels)

            if selected_action == -1 or selected_action is None:
                # User cancelled
                return

            action = paths[selected_action]

        # Add the shortcut to the menu the user has selected
        # Load existing main menu items
        menuitems = data_func.get_shortcuts(all_label_ids[selected_menu], processShortcuts=False)
        data_func.clear_label_id()

        # Generate a new labelID
        new_label_id = data_func.get_label_id(label, action)

        # Write the updated mainmenu.DATA.xml
        newelement = ETree.SubElement(menuitems.getroot(), "shortcut")
        ETree.SubElement(newelement, "label").text = label
        ETree.SubElement(newelement, "label2").text = "32024"  # Custom shortcut
        ETree.SubElement(newelement, "icon").text = icon
        ETree.SubElement(newelement, "thumb")
        ETree.SubElement(newelement, "action").text = action

        data_func.indent(menuitems.getroot())
        path = data_func.data_xml_filename(DATA_PATH,
                                           data_func.slugify(all_label_ids[selected_menu], True))
        menuitems.write(path, encoding="UTF-8")

        if is_node and selected_menu == 1:
            # We're also going to write a submenu
            menuitems = ETree.ElementTree(ETree.Element("shortcuts"))

            for item in json_response['result']['files']:
                if item["filetype"] == "directory":
                    newelement = ETree.SubElement(menuitems.getroot(), "shortcut")
                    ETree.SubElement(newelement, "label").text = item["label"]
                    ETree.SubElement(newelement, "label2").text = "32024"  # Custom shortcut
                    ETree.SubElement(newelement, "icon").text = item["thumbnail"]
                    ETree.SubElement(newelement, "thumb")
                    ETree.SubElement(newelement, "action").text = \
                        "ActivateWindow(%s,%s,return)" % (window, item["file"])

            data_func.indent(menuitems.getroot())
            path = data_func.data_xml_filename(DATA_PATH, data_func.slugify(new_label_id, True))
            menuitems.write(path, encoding="UTF-8")

        # Mark that the menu needs to be rebuilt
        HOME_WINDOW.setProperty("skinshortcuts-reloadmainmenu", "True")

        # And tell the user it all worked
        xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(32090))

    @staticmethod
    def extract_id(path):
        # Extract the ID of an item from its path
        item_id = path
        if "?" in item_id:
            item_id = item_id.rsplit("?", 1)[0]

        if item_id.endswith("/"):
            item_id = item_id[:-1]

        item_id = item_id.rsplit("/", 1)[1]

        return item_id

    # ##############################################
    # ### Functions to externally set properties ###
    # ##############################################

    # noinspection PyDictCreation
    @staticmethod
    def set_properties(properties, values, label_id, group, data_func):
        # This function will take a list of properties and values and apply them to the
        # main menu item with the given labelID
        if not group:
            group = "mainmenu"

        # Split up property names and values
        property_names = properties.split("|")
        property_values = values.replace("::INFO::", "$INFO").split("|")

        label_id_values = label_id.split("|")
        if len(label_id_values) == 0:
            # No labelID passed in, lets assume we were called in error
            return

        if len(property_names) == 0:
            # No values passed in, lets assume we were called in error
            return

        # Get user confirmation that they want to make these changes
        message = "Set %s property to %s?" % (property_names[0], property_values[0])
        if len(property_names) == 2:
            message += "[CR](and 1 other property)"

        elif len(property_names) > 2:
            message += "[CR](and %d other properties)" % (len(property_names) - 1)

        should_run = xbmcgui.Dialog().yesno(ADDON_NAME, message)
        if not should_run:
            return

        # Load the properties
        current_properties, default_properties = data_func.get_additionalproperties()
        other_properties, requires, _ = data_func.get_property_requires()

        # If there aren't any current_properties, use the default_properties instead
        if current_properties == [None]:
            current_properties = default_properties

        # Pull out all properties into multi-dimensional dicts
        all_props = {}
        all_props[group] = {}
        for current_property in current_properties:
            # If the group isn't in all_props, add it
            if current_property[0] not in all_props:
                all_props[current_property[0]] = {}

            # If the labelID isn't in the all_props[ group ], add it
            if current_property[1] not in list(all_props[current_property[0]].keys()):
                all_props[current_property[0]][current_property[1]] = {}

            # And add the property to all_props[ group ][ labelID ]
            if current_property[3] is not None:
                all_props[current_property[0]][current_property[1]][current_property[2]] = \
                    current_property[3]

        # Loop through the properties we've been asked to set
        for count, property_name in enumerate(property_names):
            # Set the new value
            log("Setting %s to %s" % (property_name, property_values[count]))
            if len(label_id_values) != 1:
                label_id = label_id_values[count]

            if label_id not in all_props[group]:
                all_props[group][label_id] = {}

            all_props[group][label_id][property_name] = property_values[count]

            # Remove any properties whose requirements haven't been met
            for key in other_properties:
                if key in all_props[group][label_id] and key in requires and \
                        requires[key] not in all_props[group][label_id]:
                    # This properties requirements aren't met
                    log("Removing value %s" % key)
                    all_props[group][label_id].pop(key)

        # Build the list of all properties to save
        save_data = []
        for save_group in list(all_props.keys()):
            for save_label_id in all_props[save_group]:
                for save_property in all_props[save_group][save_label_id]:
                    save_data.append([save_group, save_label_id, save_property,
                                      all_props[save_group][save_label_id][save_property]])

        write_properties(save_data)

        # The properties will only be used if the .DATA.xml file exists in the
        # addon_data folder( otherwise the script will use the default values),
        # so we're going to open and write the 'group' that has been passed to us
        menuitems = data_func.get_shortcuts(group, processShortcuts=False)
        data_func.indent(menuitems.getroot())
        path = data_func.data_xml_filename(DATA_PATH, data_func.slugify(group, True))
        menuitems.write(path, encoding="UTF-8")

        log("Properties updated")

        # Mark that the menu needs to be rebuilt
        HOME_WINDOW.setProperty("skinshortcuts-reloadmainmenu", "True")

    @staticmethod
    def _modify_path_and_parts(path):
        video_path = "library://video/"
        music_path = "library://music/"
        path_start = None
        path_end = None

        path = path.replace("videodb://", video_path)
        path = path.replace("musicdb://", music_path)

        if path.endswith((".xml", ".xml/")):
            path = path.rstrip("/")[:-3]

        if video_path.rstrip('/') in path:
            path_start = video_path.rstrip('/')
            path_end = "video"

        elif music_path.rstrip('/') in path:
            path_start = music_path.rstrip('/')
            path_end = "music"

        return path, path_start, path_end

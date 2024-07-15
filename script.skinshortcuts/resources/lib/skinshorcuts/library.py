# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import ast
import os
import xml.etree.ElementTree as ETree
from traceback import print_exc
from urllib.parse import unquote
from urllib.request import url2pathname
from xml.dom.minidom import parse

import xbmc
import xbmcgui
import xbmcvfs

from . import datafunctions
from . import jsonrpc
from . import nodefunctions
from .common import log
from .common import read_file
from .common_utils import ShowDialog
from .constants import ADDON_ID
from .constants import CWD
from .constants import DATA_PATH
from .constants import KODI_PATH
from .constants import KODI_VERSION
from .constants import LANGUAGE
from .constants import PROFILE_PATH


def kodiwalk(path, string_force=False):
    files = []

    json_response = jsonrpc.files_get_directory(str(path))
    if not json_response:
        return []

    for item in json_response['result']['files']:
        if 'file' in item and 'filetype' in item and 'label' in item:
            if item['filetype'] == 'directory' and \
                    not item['file'].endswith(('.xsp', '.m3u', '.xml/', '.xml')):
                if string_force and item['file'].startswith(string_force):
                    files = files + kodiwalk(xbmcvfs.translatePath(item['file']), string_force)
                else:
                    files = files + kodiwalk(item['file'], string_force)

            else:
                if string_force and item['file'].startswith(string_force):
                    files.append({
                        'path': xbmcvfs.translatePath(item['file']),
                        'label': item['label']
                    })
                else:
                    files.append({
                        'path': item['file'],
                        'label': item['label']
                    })

    return files


# noinspection PyListCreation
class LibraryFunctions:
    def __init__(self):
        self.node_func = nodefunctions.NodeFunctions()
        self.data_func = datafunctions.DataFunctions()

        # Dictionary to make checking whether things are loaded easier
        self.loaded = {
            "common": [False, "common shortcuts"],
            "more": [False, "more commands"],
            "videolibrary": [False, "video library"],
            "musiclibrary": [False, "music library"],
            "librarysources": [False, "library sources"],
            "pvrlibrary": [False, "live tv"],
            "radiolibrary": [False, "live radio"],
            "playlists": [False, "playlists"],
            "addons": [False, "add-ons"],
            "favourites": [False, "favourites"],
            "upnp": [False, "upnp sources"],
            "settings": [False, "settings"],
            "widgets": [False, "widgets"]
        }

        self.widget_playlists_list = []

        # Empty dictionary for different shortcut types
        self.dictionary_groupings = {
            "common": None,
            "commands": None,
            "video": None,
            "movie": None,
            "movie-flat": None,
            "tvshow": None,
            "tvshow-flat": None,
            "musicvideo": None,
            "musicvideo-flat": None,
            "customvideonode": None,
            "customvideonode-flat": None,
            "videosources": None,
            "pvr": None,
            "radio": None,
            "pvr-tv": None,
            "pvr-radio": None,
            "music": None,
            "musicsources": None,
            "picturesources": None,
            "playlist-video": None,
            "playlist-audio": None,
            "addon-program": None,
            "addon-program-plugin": None,
            "addon-video": None,
            "addon-audio": None,
            "addon-image": None,
            "favourite": None,
            "settings": None,
            "widgets": None,
            "widgets-classic": []
        }
        self.folders = {}
        self.folders_count = 0

        # Widget providers, for auto-installing
        self.widget_providers = [
            ["service.library.data.provider", None, "Library Data Provider"],
            ["script.extendedinfo", None, "ExtendedInfo Script"],
            ["service.smartish.widgets",
             "Skin.HasSetting(enable.smartish.widgets)",
             "Smart(ish) Widgets"]
        ]
        self.allow_widget_install = False
        self.skinhelper_widget_install = True

        self.use_default_thumb_as_icon = None

        self.install_widget = False
        self.loaded_favourites = False
        self.fav_list = None

    def load_library(self, library):
        # Common entry point for loading available shortcuts

        # Handle whether the shortcuts are already loaded/loading
        if self.loaded[library][0] is True:
            return True

        if self.loaded[library][0] == "Loading":
            # The list is currently being populated, wait and then return it
            for _ in range(0, 50):
                if xbmc.Monitor().waitForAbort(0.1) or self.loaded[library][0] is True:
                    return True

        # We're going to populate the list
        self.loaded[library][0] = "Loading"

        # Call the function responsible for loading the library type we've been passed
        log("Listing %s..." % (self.loaded[library][1]))
        try:
            if hasattr(self, library):
                library_method = getattr(self, library)
                library_method()

            else:
                log("Unknow library method %s" % library)

        except:
            log(print_exc())
            log("Failed to load %s" % (self.loaded[library][1]))

        # Mark library type as loaded
        self.loaded[library][0] = True
        return True

    def load_all_library(self):
        # Load all library data, for use with threading
        for library in ("common", "more", "videolibrary", "musiclibrary", "pvrlibrary",
                        "radiolibrary", "librarysources", "playlists", "addons",
                        "favourites", "settings", "widgets"):
            self.load_library(library)

        # Do a JSON query for upnp sources
        # (so that they'll show first time the user asks to see them)
        if self.loaded["upnp"][0] is False:
            self.loaded["upnp"][0] = \
                jsonrpc.files_get_directory('upnp://', ["title", "file", "thumbnail"]) \
                not in (False, None)

    # ==============================================
    # === BUILD/DISPLAY AVAILABLE SHORTCUT NODES ===
    # ==============================================

    def retrieve_group(self, group, flat=True, grouping=None):
        trees = [self.data_func.get_overrides_skin(), self.data_func.get_overrides_script()]
        nodes = None
        for tree in trees:
            if flat:
                nodes = tree.find("flatgroupings")
                if nodes is not None:
                    nodes = nodes.findall("node")

            elif grouping is None:
                nodes = tree.find("groupings")

            else:
                nodes = tree.find("%s-groupings" % grouping)

            if nodes is not None:
                break

        if nodes is None:
            return ["Error", []]

        if flat:
            # Flat groupings
            count = 0
            # Cycle through nodes till we find the one specified
            for node in nodes:
                count += 1
                if "condition" in node.attrib:
                    if not xbmc.getCondVisibility(node.attrib.get("condition")):
                        group += 1
                        continue

                if "version" in node.attrib:
                    version = node.attrib.get("version")
                    if KODI_VERSION != version and \
                            self.data_func.check_version_equivalency(
                                node.attrib.get("condition"), "groupings"
                            ) is False:
                        group += 1
                        continue

                if "installWidget" in node.attrib and \
                        node.attrib.get("installWidget").lower() == "true":
                    self.install_widget = True
                else:
                    self.install_widget = False

                if count == group:
                    # We found it :)
                    return node.attrib.get("label"), self.build_node_listing(node, True)

            return ["Error", []]

        # Hierarchical groupings
        if group == "":
            # We're going to get the root nodes
            self.install_widget = False
            window_title = LANGUAGE(32048)
            if grouping == "widget":
                window_title = LANGUAGE(32044)

            return [window_title, self.build_node_listing(nodes, False)]

        groups = group.split(",")

        nodes = ["", nodes]
        for group_num in groups:
            nodes = self.get_node(nodes[1], int(group_num))

        return [nodes[0], self.build_node_listing(nodes[1], False)]

    def get_node(self, tree, number):
        for idx, subnode in enumerate(tree):
            # If not visible, skip it
            if "condition" in subnode.attrib:
                if not xbmc.getCondVisibility(subnode.attrib.get("condition")):
                    number += 1
                    continue

            if "version" in subnode.attrib:
                version = subnode.attrib.get("version")
                if KODI_VERSION != version and \
                        self.data_func.check_version_equivalency(
                            subnode.attrib.get("condition"), "groupings"
                        ) is False:
                    number += 1
                    continue

            if "installWidget" in subnode.attrib and \
                    subnode.attrib.get("installWidget").lower() == "true":
                self.install_widget = True
            else:
                self.install_widget = False

            if idx + 1 == number:
                label = self.data_func.local(subnode.attrib.get("label"))[2]
                return [label, subnode]

        return []

    def build_node_listing(self, nodes, flat):
        return_list = []
        count = 0
        for node in nodes:
            if "condition" in node.attrib:
                if not xbmc.getCondVisibility(node.attrib.get("condition")):
                    continue

            if "version" in node.attrib:
                version = node.attrib.get("version")
                if KODI_VERSION != version and \
                        self.data_func.check_version_equivalency(
                            node.attrib.get("condition"), "groupings"
                        ) is False:
                    continue

            count += 1
            if node.tag == "content":
                return_list = return_list + self.retrieve_content(node.text)

            if node.tag == "shortcut":
                shortcut_item = self.create(
                    [node.text,
                     node.attrib.get("label"),
                     node.attrib.get("type"),
                     {
                         "icon": node.attrib.get("icon")
                     }]
                )

                if "widget" in node.attrib:
                    # This is a widget shortcut, so add the relevant widget information
                    shortcut_item.setProperty("widget", node.attrib.get("widget"))
                    if "widgetName" in node.attrib:
                        shortcut_item.setProperty("widgetName", node.attrib.get("widgetName"))
                    else:
                        shortcut_item.setProperty("widgetName", node.attrib.get("label"))

                    shortcut_item.setProperty("widgetPath", node.text)
                    if "widgetType" in node.attrib:
                        shortcut_item.setProperty("widgetType", node.attrib.get("widgetType"))
                    else:
                        shortcut_item.setProperty("widgetType", "")

                    if "widgetTarget" in node.attrib:
                        shortcut_item.setProperty("widgetTarget", node.attrib.get("widgetTarget"))
                    else:
                        shortcut_item.setProperty("widgetTarget", "")

                return_list.append(shortcut_item)
                # return_list.append( self.create( [node.text, node.attrib.get( "label" ),
                # node.attrib.get( "type" ), {"icon": node.attrib.get( "icon" )}] ) )

            if node.tag == "node" and flat is False:
                return_list.append(self.create(
                    ["||NODE||%s" % str(count), node.attrib.get("label"), "", {
                        "icon": "DefaultFolder.png"
                    }]))

        # Override icons
        tree = self.data_func.get_overrides_skin()
        for idx, item in enumerate(return_list):
            return_list[idx] = self._get_icon_overrides(tree, item, None)

        return return_list

    def retrieve_content(self, content):
        if content == "upnp-video":
            items = [self.create(["||UPNP||", "32070", "32069", {
                "icon": "DefaultFolder.png"
            }])]

        elif content == "upnp-music":
            items = [self.create(["||UPNP||", "32070", "32073", {
                "icon": "DefaultFolder.png"
            }])]

        elif self.dictionary_groupings[content] is None:
            # The data hasn't been loaded yet
            items = self.load_grouping(content)

        else:
            items = self.dictionary_groupings[content]

        if items is not None:
            items = self.check_for_folder(items)
        else:
            items = []

        # Add widget information for video/audio nodes
        if content in ["video", "music"]:
            # Video nodes - add widget information
            for listitem in items:
                path = listitem.getProperty("path")
                if path.lower().startswith("activatewindow"):
                    path = self.data_func.get_list_property(path)
                    listitem.setProperty("widget", "Library")
                    if content == "video":
                        listitem.setProperty("widgetType", "video")
                        listitem.setProperty("widgetTarget", "videos")

                    else:
                        listitem.setProperty("widgetType", "audio")
                        listitem.setProperty("widgetTarget", "music")

                    listitem.setProperty("widgetName", listitem.getLabel())
                    listitem.setProperty("widgetPath", path)

                    widget_type = self.node_func.get_media_type(path)
                    if widget_type != "unknown":
                        listitem.setProperty("widgetType", widget_type)

        # Check for any icon overrides for these items
        tree = self.data_func.get_overrides_skin()

        for idx, item in enumerate(items):
            items[idx] = self._get_icon_overrides(tree, item, content)

        return items

    def check_for_folder(self, items):
        # This function will check for any folders in the listings that are being returned
        # and, if found, move their sub-items into a property
        return_items = []
        for item in items:
            if isinstance(item, list):
                self.folders_count += 1
                self.folders[str(self.folders_count)] = item[1]
                new_item = item[0]
                new_item.setProperty("folder", str(self.folders_count))
                return_items.append(new_item)

            else:
                return_items.append(item)

        return return_items

    def load_grouping(self, content):
        if content in ("movie", "tvshow", "musicvideo", "customvideonode", "movie-flat",
                       "tvshow-flat", "musicvideo-flat", "customvideonode-flat"):
            # These have been deprecated
            return []

        # Display a busy dialog
        dialog = xbmcgui.DialogProgress()
        dialog.create("Skin Shortcuts", LANGUAGE(32063))

        # We'll be called if the data for a wanted group hasn't been loaded yet
        if content == "common":
            self.load_library("common")

        elif content == "commands":
            self.load_library("more")

        elif content == "video":
            self.load_library("videolibrary")

        elif content in ("videosources", "musicsources", "picturesources"):
            self.load_library("librarysources")

        elif content == "music":
            self.load_library("musiclibrary")

        elif content in ("pvr", "pvr-tv", "pvr-radio"):
            self.load_library("pvrlibrary")

        elif content == "radio":
            self.load_library("radiolibrary")

        elif content in ("playlist-video", "playlist-audio"):
            self.load_library("playlists")

        elif content in ("addon-program", "addon-video", "addon-audio", "addon-image"):
            self.load_library("addons")

        elif content == "favourite":
            self.load_library("favourites")

        elif content == "settings":
            self.load_library("settings")

        elif content == "widgets":
            self.load_library("widgets")

        # The data has now been loaded, return it
        dialog.close()

        return self.dictionary_groupings[content]

    def flat_groupings_count(self):
        # Return how many nodes there are in the the flat grouping
        tree = self.data_func.get_overrides_script()
        if tree is None:
            return 1

        groupings = tree.find("flatgroupings")
        nodes = groupings.findall("node")

        count = 0
        for node in nodes:
            if "condition" in node.attrib:
                if not xbmc.getCondVisibility(node.attrib.get("condition")):
                    continue

            if "version" in node.attrib:
                if KODI_VERSION != node.attrib.get("version"):
                    continue

            count += 1

        return count

    def add_to_dictionary(self, group, content):
        # This function adds content to the dictionaryGroupings - including
        # adding any skin-provided shortcuts to the group
        tree = self.data_func.get_overrides_skin()

        # Search for skin-provided shortcuts for this group
        original_group = group
        if group.endswith("-flat"):
            group = group.replace("-flat", "")

        if group not in ["movie", "tvshow", "musicvideo"]:
            for elem in tree.findall("shortcut"):
                if "grouping" in elem.attrib:
                    if group == elem.attrib.get("grouping"):
                        # We want to add this shortcut
                        label = elem.attrib.get("label")
                        item_type = elem.attrib.get("type")
                        thumb = elem.attrib.get("thumbnail")
                        icon = elem.attrib.get("icon")

                        action = elem.text

                        # if label.isdigit():
                        #    label = "::LOCAL::%s" % label

                        if item_type is None:
                            item_type = "32024"
                        # elif item_type.isdigit():
                        #    item_type = "::LOCAL::%s" % item_type

                        if icon is None:
                            icon = ""
                        if thumb is None:
                            thumb = ""

                        listitem = self.create([action, label, item_type, {
                            "icon": icon,
                            "thumb": thumb
                        }])

                        if "condition" in elem.attrib:
                            if xbmc.getCondVisibility(elem.attrib.get("condition")):
                                content.insert(0, listitem)
                        else:
                            content.insert(0, listitem)

                elif group == "common":
                    # We want to add this shortcut
                    label = elem.attrib.get("label")
                    item_type = elem.attrib.get("type")
                    thumb = elem.attrib.get("thumbnail")
                    icon = elem.attrib.get("icon")

                    action = elem.text

                    # if label.isdigit():
                    #    label = "::LOCAL::%s" % label

                    if item_type is None:
                        item_type = "32024"
                    # elif item_type.isdigit():
                    #    item_type = "::LOCAL::%s" % item_type

                    if item_type is None or item_type == "":
                        item_type = "Skin Provided"

                    if icon is None:
                        icon = ""

                    if thumb is None:
                        thumb = ""

                    listitem = self.create([action, label, item_type, {
                        "icon": icon,
                        "thumb": thumb
                    }])

                    if "condition" in elem.attrib:
                        if xbmc.getCondVisibility(elem.attrib.get("condition")):
                            content.append(listitem)

                    else:
                        content.append(listitem)

        self.dictionary_groupings[original_group] = content

    # ================================
    # === BUILD AVAILABLE SHORTCUT ===
    # ================================

    def create(self, item, allow_override_label=True):
        # Retrieve label
        local_label = self.data_func.local(item[1])[0]

        # Create localised label2
        display_label_2 = self.data_func.local(item[2])[2]
        shortcut_type = self.data_func.local(item[2])[0]

        if allow_override_label:
            # Check for a replaced label
            replacement_label = self.data_func.check_shortcut_label_override(item[0])
            if replacement_label is not None:

                local_label = self.data_func.local(replacement_label[0])[0]

                if len(replacement_label) == 2:
                    # We're also overriding the type
                    display_label_2 = self.data_func.local(replacement_label[1])[2]
                    shortcut_type = self.data_func.local(replacement_label[1])[0]

        # Try localising it
        display_label = self.data_func.local(local_label)[2]

        if display_label.startswith("$NUMBER["):
            display_label = display_label[8:-1]

        # Create localised label2
        display_label_2 = self.data_func.local(display_label_2)[2]
        shortcut_type = self.data_func.local(shortcut_type)[0]

        # If either display_label starts with a $, ask Kodi to parse it for us
        if display_label.startswith("$"):
            display_label = xbmc.getInfoLabel(display_label)

        if display_label_2.startswith("$"):
            display_label_2 = xbmc.getInfoLabel(display_label_2)

        # If this launches our explorer, append a notation to the display_label
        localized_only = False
        if item[0].startswith("||"):
            display_label = "%s  >" % display_label
            # We'll also mark that we don't want to use a non-localised labelID, as this
            # causes issues with some folders picking up overridden icons incorrectly
            localized_only = True

        # Get the items labelID
        self.data_func.clear_label_id()
        label_id = self.data_func.get_label_id(
            self.data_func.create_nice_name(self.data_func.local(local_label)[0],
                                            localized_only=localized_only),
            item[0],
            localized_only=localized_only
        )

        # Retrieve icon and thumbnail
        if item[3]:
            if "icon" in list(item[3].keys()) and item[3]["icon"] is not None:
                icon = item[3]["icon"]
            else:
                icon = "DefaultShortcut.png"

            if "thumb" in list(item[3].keys()):
                thumbnail = item[3]["thumb"]
            else:
                thumbnail = None

        else:
            icon = "DefaultShortcut.png"
            thumbnail = None

        # Check if the option to use the thumb as the icon is enabled
        if self.use_default_thumb_as_icon is None:
            # Retrieve the choice from the overrides.xml
            tree = self.data_func.get_overrides_skin()
            node = tree.getroot().find("useDefaultThumbAsIcon")
            if node is None:
                self.use_default_thumb_as_icon = False

            else:
                self.use_default_thumb_as_icon = node.text.lower() == "true"

        used_default_thumb_as_icon = False
        if self.use_default_thumb_as_icon is True and thumbnail is not None:
            icon = thumbnail
            thumbnail = None
            used_default_thumb_as_icon = True

        # If the icon starts with a $, ask Kodi to parse it for us
        display_icon = icon
        icon_is_var = False
        if icon.startswith("$"):
            display_icon = xbmc.getInfoLabel(icon)
            icon_is_var = True

        # special treatment for image resource addons
        if icon.startswith("resource://"):
            icon_is_var = True

        # If the skin doesn't have the icon, replace it with DefaultShortcut.png
        if (not display_icon or not xbmc.skinHasImage(display_icon)) and not icon_is_var:
            if not used_default_thumb_as_icon:
                display_icon = "DefaultShortcut.png"

        # Build listitem
        if thumbnail is not None:
            listitem = xbmcgui.ListItem(label=display_label, label2=display_label_2, offscreen=True)
            listitem.setArt({
                'icon': display_icon,
                'thumb': thumbnail
            })
            listitem.setProperty("thumbnail", thumbnail)

        else:
            listitem = xbmcgui.ListItem(label=display_label, label2=display_label_2, offscreen=True)
            listitem.setArt({
                'icon': ''
            })

        listitem.setProperty("path", item[0])
        listitem.setProperty("localizedString", local_label)
        listitem.setProperty("shortcutType", shortcut_type)
        listitem.setProperty("icon", display_icon)
        listitem.setProperty("tempLabelID", label_id)
        listitem.setProperty("defaultLabel", label_id)

        if display_icon != icon:
            listitem.setProperty("untranslatedIcon", icon)

        return listitem

    def _get_icon_overrides(self, tree, item, content, set_to_default=True):
        if tree is None:
            return item

        oldicon = None
        newicon = item.getProperty("icon")
        for elem in tree.findall("icon"):
            if oldicon is None:
                if ("labelID" in elem.attrib and
                    elem.attrib.get("labelID") == item.getProperty("tempLabelID")) or \
                        ("image" in elem.attrib and elem.attrib.get("image") ==
                         item.getProperty("icon")):

                    # LabelID matched
                    if "grouping" in elem.attrib:
                        if elem.attrib.get("grouping") == content:
                            # Group also matches - change icon
                            oldicon = item.getProperty("icon")
                            newicon = elem.text

                    elif "group" not in elem.attrib:
                        # No group - change icon
                        oldicon = item.getProperty("icon")
                        newicon = elem.text

        # If the icon doesn't exist, set icon to default
        set_default = False
        if not xbmc.skinHasImage(newicon) and set_to_default is True:
            oldicon = item.getProperty("icon")
            set_default = True

        if oldicon is not None:
            # we found an icon override
            item.setProperty("icon", newicon)
            item.setArt({
                'icon': 'newicon'
            })

        if set_default is True:
            item = self._get_icon_overrides(tree, item, content, False)

        return item

    # ===================================
    # === LOAD VIDEO LIBRARY HIERARCHY ===
    # ===================================

    def videolibrary(self):
        # Try loading custom nodes first
        try:
            if self._parse_library_nodes("video", "custom") is False:
                log("Failed to load custom video nodes")
                self._parse_library_nodes("video", "default")

        except:
            log(print_exc())
            log("Failed to load custom video nodes")
            try:
                # Try loading default nodes
                self._parse_library_nodes("video", "default")

            except:
                # Empty library
                log(print_exc())
                log("Failed to load default video nodes")

    def _parse_library_nodes(self, library, node_type):
        # items = {"video":[], "movies":[], "tvshows":[], "musicvideos":[], "custom":{}}
        if library == "video":
            window_id = "Videos"
            prefix = "library://video"
            action = "||VIDEO||"

        elif library == "music":
            window_id = "music"
            prefix = "library://music"
            action = "||AUDIO||"

        else:
            return None

        rootdir = os.path.join(PROFILE_PATH, "library", library)
        if node_type == "custom":
            log("Listing custom %s nodes..." % library)

        else:
            rootdir = os.path.join(KODI_PATH, "system", "library", library)
            log("Listing default %s nodes..." % library)

        nodes = self.node_func.get_nodes(rootdir, prefix)
        if nodes is False or len(nodes) == 0:
            return False

        items = []

        for key in nodes:
            # 0 = Label
            # 1 = Icon
            # 2 = Path
            # 3 = Type
            # 4 = Order
            # 5 = Media type (not folders...?)

            # make sure the path ends with a trailing slash to prevent weird kodi behaviour
            if "/" in nodes[key][2] and not nodes[key][2].endswith("/"):
                nodes[key][2] += "/"

            if nodes[key][3] == "folder":
                item = self.create(
                    ["%s%s" % (action, nodes[key][2]), nodes[key][0], nodes[key][3], {
                        "icon": nodes[key][1]
                    }]
                )

            elif nodes[key][3] == "grouped":
                item = self.create(
                    ["%s%s" % (action, nodes[key][2]), nodes[key][0], nodes[key][3], {
                        "icon": nodes[key][1]
                    }]
                )

            else:
                item = self.create(
                    ["ActivateWindow(%s,%s,return)" % (window_id, nodes[key][2]),
                     nodes[key][0], nodes[key][3], {
                         "icon": nodes[key][1]
                     }]
                )

            if nodes[key][5] is not None:
                item.setProperty("widgetType", nodes[key][5])
                item.setProperty("widgetTarget", library)

            items.append(item)

        self.add_to_dictionary(library, items)

        return True

    # ============================
    # === LOAD OTHER LIBRARIES ===
    # ============================

    def common(self):
        # Videos, Movies, TV Shows, Live TV, Music, Music Videos, Pictures, Weather, Programs,
        # Play dvd, eject tray
        # Settings, File Manager, Profiles, System Info

        listitems = [
            self.create(["ActivateWindow(Videos)", "3", "32034", {
                "icon": "DefaultVideo.png"
            }]),
            self.create(["ActivateWindow(Videos,videodb://movies/titles/,return)", "342", "32034", {
                "icon": "DefaultMovies.png"
            }]),
            self.create(["ActivateWindow(Videos,videodb://tvshows/titles/,return)", "20343",
                         "32034", {
                             "icon": "DefaultTVShows.png"
                         }]),
            self.create(["ActivateWindow(TVGuide)", "32022", "32034", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(RadioGuide)", "32087", "32034", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(Music)", "2", "32034", {
                "icon": "DefaultMusicAlbums.png"
            }]),
            self.create(["PlayerControl(PartyMode)", "589", "32034", {
                "icon": "DefaultMusicAlbums.png"
            }]),
            self.create(["PlayerControl(PartyMode(Video))", "32108", "32034", {
                "icon": "DefaultMusicVideos.png"
            }]),
            self.create(["ActivateWindow(Videos,videodb://musicvideos/titles/,return)", "20389",
                         "32034", {
                             "icon": "DefaultMusicVideos.png"
                         }]),
            self.create(["ActivateWindow(Pictures)", "10002", "32034", {
                "icon": "DefaultPicture.png"
            }]),
            self.create(["ActivateWindow(Weather)", "12600", "32034", {
                "icon": "Weather.png"
            }]),
            self.create(["ActivateWindow(Programs,Addons,return)", "10001", "32034", {
                "icon": "DefaultProgram.png"
            }]),
            self.create(["PlayDVD", "32032", "32034", {
                "icon": "DefaultDVDFull.png"
            }]),
            self.create(["EjectTray()", "32033", "32034", {
                "icon": "DefaultDVDFull.png"
            }]),
            self.create(["ActivateWindow(Settings)", "10004", "32034", {
                "icon": "Settings.png"
            }]),
            self.create(["ActivateWindow(FileManager)", "7", "32034", {
                "icon": "DefaultFolder.png"
            }]),
            self.create(["ActivateWindow(Profiles)", "13200", "32034", {
                "icon": "UnknownUser.png"
            }]),
            self.create(["ActivateWindow(SystemInfo)", "10007", "32034", {
                "icon": "SystemInfo.png"
            }]),
            self.create(["ActivateWindow(EventLog,events://,return)", "14111", "32034", {
                "icon": "Events.png"
            }]),
            self.create(["ActivateWindow(Favourites)", "1036", "32034", {
                "icon": "Favourites.png"
            }]),
        ]
        self.add_to_dictionary("common", listitems)

    def more(self):
        listitems = [
            self.create(["Reboot", "13013", "32054", {
                "icon": "Reboot.png"
            }]),
            self.create(["ShutDown", "13005", "32054", {
                "icon": "Shutdown.png"
            }]),
            self.create(["PowerDown", "13016", "32054", {
                "icon": "PowerDown.png"
            }]),
            self.create(["Quit", "13009", "32054", {
                "icon": "Quit.png"
            }]),
            self.create(["Hibernate", "13010", "32054", {
                "icon": "Hibernate.png"
            }]),
            self.create(["Suspend", "13011", "32054", {
                "icon": "Suspend.png"
            }]),
            self.create(["AlarmClock(shutdowntimer,XBMC.Shutdown())", "19026", "32054", {
                "icon": "ShutdownTimer.png"
            }]),
            self.create(["CancelAlarm(shutdowntimer)", "20151", "32054", {
                "icon": "CancelShutdownTimer.png"
            }]),
            self.create(["ActivateScreensaver", "360", "32054", {
                "icon": "ActivateScreensaver.png"
            }]),
            self.create(["Minimize", "13014", "32054", {
                "icon": "Minimize.png"
            }]),
            self.create(["Mastermode", "20045", "32054", {
                "icon": "Mastermode.png"
            }]),
            self.create(["RipCD", "600", "32054", {
                "icon": "RipCD.png"
            }]),
            self.create(["UpdateLibrary(video,,true)", "32046", "32054", {
                "icon": "UpdateVideoLibrary.png"
            }]),
            self.create(["UpdateLibrary(music,,true)", "32047", "32054", {
                "icon": "UpdateMusicLibrary.png"
            }]),
            self.create(["CleanLibrary(video,true)", "32055", "32054", {
                "icon": "CleanVideoLibrary.png"
            }]),
            self.create(["CleanLibrary(music,true)", "32056", "32054", {
                "icon": "CleanMusicLibrary.png"
            }]),
        ]

        if (xbmc.getCondVisibility("System.Platform.Windows") or
            xbmc.getCondVisibility("System.Platform.Linux")) and \
                not xbmc.getCondVisibility("System.Platform.Linux.RaspberryPi"):
            listitems.append(self.create(["RestartApp", "13313", "32054", {
                "icon": "RestartApp.png"
            }]))

        if xbmc.getCondVisibility("System.HasLoginScreen"):
            listitems.append(self.create(["System.LogOff", "20126", "32054", {
                "icon": "LogOff.png"
            }]))

        self.add_to_dictionary("commands", listitems)

    def settings(self):
        listitems = [
            self.create(["ActivateWindow(Settings)", "10004", "10004", {
                "icon": "Settings.png"
            }]),
            self.create(["ActivateWindow(PVRSettings)", "19020", "10004", {
                "icon": "PVRSettings.png"
            }]),
            self.create(["ActivateWindow(AddonBrowser)", "24001", "10004", {
                "icon": "DefaultAddon.png"
            }]),
            self.create(["ActivateWindow(ServiceSettings)", "14036", "10004", {
                "icon": "ServiceSettings.png"
            }]),
            self.create(["ActivateWindow(SystemSettings)", "13000", "10004", {
                "icon": "SystemSettings.png"
            }]),
            self.create(["ActivateWindow(SkinSettings)", "20077", "10004", {
                "icon": "SkinSettings.png"
            }]),
            self.create(["ActivateWindow(PlayerSettings)", "14200", "10004", {
                "icon": "PlayerSettings.png"
            }]),
            self.create(["ActivateWindow(LibrarySettings)", "14202", "10004", {
                "icon": "LibrarySettings.png"
            }]),
            self.create(["ActivateWindow(InterfaceSettings)", "14206", "10004", {
                "icon": "InterfaceSettings.png"
            }]),
        ]

        self.add_to_dictionary("settings", listitems)

    def pvrlibrary(self):
        # PVR
        listitems = [
            self.create(["ActivateWindow(TVChannels)", "19019", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(TVGuide)", "22020", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(TVRecordings)", "19017", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(TVTimers)", "19040", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(TVTimerRules)", "19138", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["ActivateWindow(TVSearch)", "137", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["PlayPvrTV", "32066", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
            self.create(["PlayPvr", "32068", "32017", {
                "icon": "DefaultTVShows.png"
            }]),
        ]
        self.add_to_dictionary("pvr", listitems)

        # Add tv channels
        listitems = []
        json_response = jsonrpc.pvr_get_channels("alltv", ["thumbnail", "channeltype", "hidden",
                                                           "locked", "channel", "lastplayed"])

        # Add all directories returned by the json query
        if json_response:
            for item in json_response['result']['channels']:
                listitems.append(self.create(
                    ["pvr-channel://%s" % str(item['channelid']), item['label'], "::SCRIPT::32076",
                     {
                         "icon": "DefaultTVShows.png",
                         "thumb": item["thumbnail"]
                     }]
                ))

        self.add_to_dictionary("pvr-tv", listitems)

        # Add radio channels
        listitems = []
        json_response = jsonrpc.pvr_get_channels("allradio", ["thumbnail", "channeltype", "hidden",
                                                              "locked", "channel", "lastplayed"])

        # Add all directories returned by the json query
        if json_response:
            for item in json_response['result']['channels']:
                listitems.append(self.create(
                    ["pvr-channel://%s" % str(item['channelid']), item['label'], "::SCRIPT::32077",
                     {
                         "icon": "DefaultTVShows.png",
                         "thumb": item["thumbnail"]
                     }]
                ))

        log("Found %s radio channels" % str(len(listitems)))
        self.add_to_dictionary("pvr-radio", listitems)

    def radiolibrary(self):
        # PVR
        listitems = [
            self.create(["ActivateWindow(RadioChannels)", "19019", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["ActivateWindow(RadioGuide)", "22020", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["ActivateWindow(RadioRecordings)", "19017", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["ActivateWindow(RadioTimers)", "19040", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["ActivateWindow(RadioTimerRules)", "19138", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["ActivateWindow(RadioSearch)", "137", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["PlayPvrRadio", "32067", "32087", {
                "icon": "DefaultAudio.png"
            }]),
            self.create(["PlayPvr", "32068", "32087", {
                "icon": "DefaultAudio.png"
            }]),
        ]

        self.add_to_dictionary("radio", listitems)

    def musiclibrary(self):
        # Try loading custom nodes first
        try:
            if self._parse_library_nodes("music", "custom") is False:
                log("Failed to load custom music nodes")
                self._parse_library_nodes("music", "default")

        except:
            log(print_exc())
            log("Failed to load custom music nodes")
            try:
                # Try loading default nodes
                self._parse_library_nodes("music", "default")

            except:
                # Empty library
                log(print_exc())
                log("Failed to load default music nodes")

        # Do a JSON query for upnp sources (so that they'll show first time
        # the user asks to see them)
        if self.loaded["upnp"][0] is False:
            self.loaded["upnp"][0] = \
                jsonrpc.files_get_directory('upnp://', ["title", "file", "thumbnail"]) \
                not in (False, None)

    def librarysources(self):
        # Add video sources
        listitems = []
        json_response = jsonrpc.files_get_sources("video")

        # Add all directories returned by the json query
        if json_response:
            for item in json_response['result']['sources']:
                listitems.append(self.create(
                    ["||SOURCE||%s" % item['file'], item['label'], "32069", {
                        "icon": "DefaultFolder.png"
                    }]
                ))

        self.add_to_dictionary("videosources", listitems)

        log("Found %s video sources" % str(len(listitems)))

        # Add audio sources
        listitems = []
        json_response = jsonrpc.files_get_sources("music")

        # Add all directories returned by the json query
        if json_response:
            for item in json_response['result']['sources']:
                listitems.append(self.create(
                    ["||SOURCE||%s" % item['file'], item['label'], "32073", {
                        "icon": "DefaultFolder.png"
                    }]
                ))

        self.add_to_dictionary("musicsources", listitems)

        log("Found %s audio sources" % str(len(listitems)))

        # Add picture sources
        listitems = []
        json_response = jsonrpc.files_get_sources("pictures")

        # Add all directories returned by the json query
        if json_response:
            for item in json_response['result']['sources']:
                listitems.append(self.create(
                    ["||SOURCE||%s" % item['file'], item['label'], "32089", {
                        "icon": "DefaultFolder.png"
                    }]
                ))

        self.add_to_dictionary("picturesources", listitems)

        log("Found %s picture sources" % str(len(listitems)))

    def playlists(self):
        audiolist = []
        videolist = []
        paths = [
            ['special://videoplaylists/', '32004', 'Videos'],
            ['special://musicplaylists/', '32005', 'Music'],
            ["special://skin/playlists/", '32059', None],
            ["special://skin/extras/", '32059', None]
        ]

        for path in paths:
            count = 0
            if not xbmcvfs.exists(path[0]):
                continue

            for file in kodiwalk(path[0]):
                try:
                    playlist = file['path']
                    label = file['label']
                    playlistfile = xbmcvfs.translatePath(playlist)
                    media_library = path[2]

                    if playlist.endswith('.xsp'):
                        contents_data = read_file(playlistfile)
                        xmldata = ETree.fromstring(contents_data)
                        media_type = "unknown"
                        try:
                            iterator = xmldata.iter()

                        except:
                            # noinspection PyDeprecation
                            iterator = xmldata.getiterator()

                        media_content = ''
                        for line in iterator:

                            if line.tag == "smartplaylist":
                                media_type = line.attrib['type']
                                if media_type in ('movies', 'tvshows', 'seasons', 'episodes',
                                                  'musicvideos', 'sets'):
                                    media_library = "Videos"
                                    media_content = "video"

                                elif media_type in ('albums', 'artists', 'songs'):
                                    media_library = "Music"
                                    media_content = "music"

                            if line.tag == "name" and media_library is not None:
                                name = line.text
                                if not name:
                                    name = label

                                # Create a list item
                                listitem = self.create(
                                    ["::PLAYLIST>%s::" % media_library, name, path[1], {
                                        "icon": "DefaultPlaylist.png"
                                    }]
                                )
                                listitem.setProperty("action-play", "PlayMedia(%s)" % playlist)
                                listitem.setProperty("action-show",
                                                     "ActivateWindow(%s,%s,return)" %
                                                     (media_library, playlist))
                                listitem.setProperty("action-party",
                                                     "PlayerControl(PartyMode(%s))" % playlist)

                                # Add widget information
                                listitem.setProperty("widget", "Playlist")
                                listitem.setProperty("widgetType", media_type)
                                listitem.setProperty("widgetTarget", media_content)
                                listitem.setProperty("widgetName", name)
                                listitem.setProperty("widgetPath", playlist)

                                if media_library == "Videos":
                                    videolist.append(listitem)
                                else:
                                    audiolist.append(listitem)

                                # Save it for the widgets list
                                self.widget_playlists_list.append(
                                    [playlist, "(%s) %s" % (LANGUAGE(int(path[1])), name), name]
                                )

                                count += 1
                                break

                    elif playlist.endswith('.m3u') and path[2] is not None:
                        name = label
                        listitem = self.create(["::PLAYLIST>%s::" % (path[2]), name, path[1], {
                            "icon": "DefaultPlaylist.png"
                        }])
                        listitem.setProperty("action-play", "PlayMedia(%s)" % playlist)
                        listitem.setProperty("action-show", "ActivateWindow(%s,%s,return)" %
                                             (path[2], playlist))
                        listitem.setProperty("action-party", "PlayerControl(PartyMode(%s))" %
                                             playlist)

                        # Add widget information
                        listitem.setProperty("widget", "Playlist")
                        listitem.setProperty("widgetName", name)
                        listitem.setProperty("widgetPath", playlist)
                        if path[2] == "Videos":
                            listitem.setProperty("widgetType", "videos")
                            listitem.setProperty("widgetTarget", "videos")
                            videolist.append(listitem)

                        else:
                            listitem.setProperty("widgetType", "songs")
                            listitem.setProperty("widgetTarget", "music")
                            audiolist.append(listitem)

                        count += 1

                except:
                    log(print_exc())
                    log("Failed to load playlist: %s" % file)

            log("[%s] %s playlists found" % (path[0], str(count)))

        self.add_to_dictionary("playlist-video", videolist)
        self.add_to_dictionary("playlist-audio", audiolist)

    @staticmethod
    def script_playlists():
        # Lazy loading of random source playlists auto-generated by the script
        # (loaded lazily as these can be created/deleted after gui has loaded)
        return_playlists = []
        try:
            log('Loading script generated playlists...')
            path = "special://profile/addon_data/%s/" % ADDON_ID
            count = 0
            for file in kodiwalk(path):
                playlist = file['path']
                playlistfile = xbmcvfs.translatePath(playlist)

                if playlist.endswith('-randomversion.xsp'):
                    contents_data = read_file(playlistfile)
                    xmldata = ETree.fromstring(contents_data)
                    try:
                        iterator = xmldata.iter()
                    except:
                        # noinspection PyDeprecation
                        iterator = xmldata.getiterator()

                    for line in iterator:
                        if line.tag == "name":
                            name = line.text
                            # Save it for the widgets list
                            # TO-DO - Localize display name
                            return_playlists.append([playlist, "(Source) %s" % name, name])

                            count += 1
                            break

            log("[%s] %s playlists found" % (path[0], str(count)))

        except:
            log(print_exc())
            log("Failed to load script generated playlists")

        return return_playlists

    def favourites(self):
        listitems = []

        fav_file = xbmcvfs.translatePath('special://profile/favourites.xml')
        if xbmcvfs.exists(fav_file):
            doc = parse(fav_file)
            listing = doc.documentElement.getElementsByTagName('favourite')

        else:
            # No favourites file found
            self.add_to_dictionary("favourite", [])
            self.loaded_favourites = True
            return True

        for favourite in listing:
            name = favourite.attributes['name'].nodeValue
            path = favourite.childNodes[0].nodeValue
            if path.lower().startswith('activatewindow') and \
                    not path.endswith(',return)'):
                path = path.rstrip(')')
                path = '%s,return)' % path

            try:
                thumb = favourite.attributes['thumb'].nodeValue

            except:
                thumb = None

            listitems.append(self.create([path, name, "32006", {
                "icon": "DefaultFolder.png",
                "thumb": thumb
            }]))

        log("%s favourites found" % str(len(listitems)))

        self.add_to_dictionary("favourite", listitems)
        self.loaded_favourites = True

        return True

    def addons(self):
        executable_items = {}
        executable_plugin_items = {}
        video_items = {}
        audio_items = {}
        image_items = {}

        contenttypes = [
            ("executable", executable_items),
            ("video", video_items),
            ("audio", audio_items),
            ("image", image_items)
        ]

        for contenttype, listitems in contenttypes:
            # listitems = {}
            shortcut_type = ""
            if contenttype == "executable":
                _ = LANGUAGE(32009)
                shortcut_type = "::SCRIPT::32009"

            elif contenttype == "video":
                _ = LANGUAGE(32010)
                shortcut_type = "::SCRIPT::32010"

            elif contenttype == "audio":
                _ = LANGUAGE(32011)
                shortcut_type = "::SCRIPT::32011"

            elif contenttype == "image":
                _ = LANGUAGE(32012)
                shortcut_type = "::SCRIPT::32012"

            if not shortcut_type:
                continue

            json_response = jsonrpc.addons_get_addons(contenttype,
                                                      ["name", "path", "thumbnail", "enabled"])

            if json_response:
                for item in json_response['result']['addons']:
                    if item['enabled'] is True:
                        path = "RunAddOn(%s)" % item['addonid']
                        if item['thumbnail'] != "":
                            thumb = item['thumbnail']
                        else:
                            thumb = None

                        listitem = self.create([path, item['name'], shortcut_type, {
                            "icon": "DefaultAddon.png",
                            "thumb": "thumb"
                        }])

                        # If this is a plugin, mark that we can browse it
                        if item["type"] == "xbmc.python.pluginsource":
                            path = "||BROWSE||%s" % item['addonid']
                            action = "RunAddOn(%s)" % item['addonid']

                            listitem.setProperty("path", path)
                            listitem.setProperty("action", action)
                            listitem.setLabel("%s  >" % listitem.getLabel())

                            # If its executable, save it to our program plugin widget list
                            if contenttype == "executable":
                                executable_plugin_items[item["name"]] = listitem

                        elif contenttype == "executable":
                            # Check if it's a program that can be run as an exectuble
                            provides = self._has_plugin_entry_point(item["path"])
                            for content in provides:
                                # For each content that it provides, add it
                                # to the add-ons for that type
                                content_data = {
                                    "video": ["::SCRIPT::32010", video_items],
                                    "audio": ["::SCRIPT::32011", audio_items],
                                    "image": ["::SCRIPT::32012", image_items],
                                    "executable": ["::SCRIPT::32009", executable_items]
                                }

                                if content in content_data:
                                    # Add it as a plugin in the relevant category
                                    other_item = self.create(
                                        [path, "%s  >" % item['name'], content_data[content][0], {
                                            "icon": "DefaultAddon.png",
                                            "thumb": thumb
                                        }]
                                    )
                                    other_item.setProperty("path", "||BROWSE||%s" % item['addonid'])
                                    other_item.setProperty("action",
                                                           "RunAddOn(%s)" % item['addonid'])
                                    content_data[content][1][item["name"]] = other_item

                                    # If it's executable, add it to our
                                    # seperate program plugins for widgets
                                    if content == "executable":
                                        executable_plugin_items[item["name"]] = other_item

                        # Save the listitem
                        listitems[item["name"]] = listitem

            if contenttype == "executable":
                self.add_to_dictionary("addon-program", self._sort_dictionary(listitems))
                self.add_to_dictionary("addon-program-plugin",
                                       self._sort_dictionary(executable_plugin_items))
                log("%s programs found (of which %s are plugins)" %
                    (str(len(listitems)), str(len(executable_plugin_items))))

            elif contenttype == "video":
                self.add_to_dictionary("addon-video", self._sort_dictionary(listitems))
                log("%s video add-ons found" % str(len(listitems)))

            elif contenttype == "audio":
                self.add_to_dictionary("addon-audio", self._sort_dictionary(listitems))
                log("%s audio add-ons found" % str(len(listitems)))

            elif contenttype == "image":
                self.add_to_dictionary("addon-image", self._sort_dictionary(listitems))
                log("%s image add-ons found" % str(len(listitems)))

    @staticmethod
    def _has_plugin_entry_point(path):
        # Check if an addon has a plugin entry point by parsing its addon.xml file
        try:
            tree = ETree.parse(os.path.join(path, "addon.xml")).getroot()
            for extension in tree.findall("extension"):
                if "point" in extension.attrib and \
                        extension.attrib.get("point") == "xbmc.python.pluginsource":
                    # Find out what content type it provides
                    provides = extension.find("provides")
                    if provides is None:
                        return []

                    return provides.text.split(" ")

        except:
            log(print_exc())

        return []

    @staticmethod
    def _detect_plugin_content(item):
        # based on the properties in the listitem we try to detect the content

        if "showtitle" not in item and "artist" not in item:
            # these properties are only returned in the json response
            # if we're looking at actual file content...
            # if it's missing it means this is a main directory listing
            # and no need to scan the underlying listitems.
            return None

        if "showtitle" not in item and "artist" not in item:
            # these properties are only returned in the json response
            # if we're looking at actual file content...
            # if it's missing it means this is a main directory listing
            # and no need to scan the underlying listitems.
            return "files"

        if "showtitle" not in item and "artist" in item:
            # AUDIO ITEMS ####
            if len(item["artist"]) != 0:
                artist = item["artist"][0]
            else:
                artist = item["artist"]

            if item["type"] == "artist" or artist == item["title"]:
                return "artists"

            if item["type"] == "album" or item["album"] == item["title"]:
                return "albums"

            if (item["type"] == "song" and "play_album" not in item["file"]) or \
                    (item["artist"] and item["album"]):
                return "songs"

        else:
            # VIDEO ITEMS ####
            if item["showtitle"] and not item["artist"]:
                # this is a tvshow, episode or season...
                if item["type"] == "season" or (item["season"] > -1 and item["episode"] == -1):
                    return "seasons"

                if item["type"] == "episode" or item["season"] > -1 and item["episode"] > -1:
                    return "episodes"

                return "tvshows"

            if item["artist"]:
                # this is a musicvideo
                return "musicvideos"

            if item["type"] == "movie" or item["imdbnumber"] or item["mpaa"] or \
                    item["trailer"] or item["studio"]:
                return "movies"

        return None

    def widgets(self):
        # Get widgets
        listitems = []

        # Load skin overrides
        tree = self.data_func.get_overrides_skin()
        elems = tree.getroot().findall("widget")
        for elem in elems:
            widget_type = None
            widget_path = None
            widget_target = None
            widget_icon = ""
            widget_name = None

            if "type" in elem.attrib:
                widget_type = elem.attrib.get("type")

            if "condition" in elem.attrib:
                if not xbmc.getCondVisibility(elem.attrib.get("condition")):
                    continue

            if "path" in elem.attrib:
                widget_path = elem.attrib.get("path")

            if "target" in elem.attrib:
                widget_target = elem.attrib.get("target")

            if "icon" in elem.attrib:
                widget_icon = elem.attrib.get("icon")

            if "name" in elem.attrib:
                widget_name = self.data_func.local(elem.attrib.get('name'))[2]

            # Save widget for button 309
            self.dictionary_groupings["widgets-classic"].append(
                [elem.text,
                 self.data_func.local(elem.attrib.get('label'))[2],
                 widget_type, widget_path, widget_icon, widget_target]
            )

            # Save widgets for button 312
            listitem = self.create(
                [elem.text, self.data_func.local(elem.attrib.get('label'))[2], "::SCRIPT::32099", {
                    "icon": widget_icon
                }]
            )

            listitem.setProperty("widget", elem.text)

            if widget_name is not None:
                listitem.setProperty("widgetName", widget_name)
            else:
                listitem.setProperty("widgetName",
                                     self.data_func.local(elem.attrib.get('label'))[2])
            if widget_type is not None:
                listitem.setProperty("widgetType", widget_type)

            if widget_path is not None:
                listitem.setProperty("widgetPath", widget_path)

            if widget_target is not None:
                listitem.setProperty("widgetTarget", widget_target)

            listitems.append(listitem)

        self.add_to_dictionary("widgets", listitems)

    @staticmethod
    def _sort_dictionary(dictionary):
        listitems = []
        for key in sorted(dictionary.keys()):  # , reverse = True):
            listitems.append(dictionary[key])

        return listitems

    # =============================
    # === ADDON/SOURCE EXPLORER ===
    # =============================

    def explorer(self, history, location, label, thumbnail, item_type, is_widget=False):
        is_library = False
        widget_type = None
        addon_type = None

        dialog_label = label[0].replace("  >", "")
        if len(label) != 1:
            dialog_label = "%s - %s" % (label[0].replace("  >", ""), label[-1].replace("  >", ""))

        listings = []

        tree = self.data_func.get_overrides_skin()

        # Shortcut to go 'up'
        if len(label) == 1:
            # This is the root, create a link to go back to select_shortcut
            listitem = self.create(["::UP::", "..", "", {}])
        else:
            # This isn't the root, create a link to go up the heirachy
            listitem = self.create(["::BACK::", "..", "", {}])

        listings.append(listitem)

        # Default action - create shortcut (do not show when we're looking at
        # the special entries from skinhelper service)
        if "script.skin.helper.service" not in location:
            create_label = "32058"
            if is_widget:
                create_label = "32100"

            listings.append(
                self._get_icon_overrides(tree,
                                         self.create(["::CREATE::", create_label, "", {}]), "")
            )

        log("Getting %s - %s" % (dialog_label, location))

        # Show a waiting dialog, then get the listings for the directory
        dialog = xbmcgui.DialogProgress()
        dialog.create(dialog_label, LANGUAGE(32063))

        # we retrieve a whole bunch of properties, needed to guess the content type properly
        json_response = jsonrpc.files_get_directory(location, ["title", "file", "thumbnail",
                                                               "episode", "showtitle", "season",
                                                               "album", "artist", "imdbnumber",
                                                               "firstaired", "mpaa", "trailer",
                                                               "studio", "art"])

        # Add all directories returned by the json query
        if json_response:
            json_result = json_response['result']['files']

            for item in json_result:
                # Handle numeric labels
                alt_label = item["label"]
                if item["label"].isnumeric():
                    alt_label = "$NUMBER[%s]" % item["label"]

                if location.startswith("library://"):
                    # Process this as a library node
                    is_library = True
                    if widget_type is None:
                        widget_type = self.node_func.get_media_type(location)

                    if item_type == "32014":
                        # Video node
                        window_id = "Videos"
                        if widget_type == "unknown":
                            widget_type = "video"
                        widget_target = "videos"

                    else:
                        # Audio node
                        window_id = "Music"
                        if widget_type == "unknown":
                            widget_type = "audio"
                        widget_target = "music"

                    if item["filetype"] == "directory":
                        thumb = None
                        if item["thumbnail"] != "":
                            thumb = item["thumbnail"]

                        listitem = self.create(
                            ["ActivateWindow(%s,%s,return)" % (window_id, item["file"]), alt_label,
                             "", {
                                 "icon": "DefaultFolder.png",
                                 "thumb": thumb
                             }]
                        )

                        if item["file"].endswith(".xml/") and \
                                self.node_func.is_grouped(item["file"]):
                            listitem = self.create([item["file"], "%s  >" % (item["label"]), "", {
                                "icon": "DefaultFolder.png",
                                "thumb": thumb
                            }])

                        # Add widget properties
                        widget_name = "%s - %s" % (label[0].replace("  >", ""), item["label"])
                        listitem.setProperty("widget", "Library")
                        listitem.setProperty("widgetName", widget_name)
                        listitem.setProperty("widgetType", widget_type)
                        listitem.setProperty("widgetTarget", widget_target)
                        listitem.setProperty("widgetPath", item["file"])

                        listings.append(self._get_icon_overrides(tree, listitem, ""))

                # some special code for smart shortcuts in script.skin.helper.service
                elif item.get("title", None) == "smartshortcut":

                    smart_shortcuts_data = ast.literal_eval(item.get("mpaa"))
                    thumb = smart_shortcuts_data["background"]

                    listitem = self.create([item["file"], alt_label, "", {
                        "icon": item.get("icon"),
                        "thumb": thumb
                    }])
                    # add all passed properties to the gui to set default background, widget etc.
                    properties = []
                    for key, value in list(smart_shortcuts_data.items()):
                        properties.append([key, value])

                    listitem.setProperty("smartShortcutProperties", repr(properties))
                    listitem.setProperty("untranslatedIcon", thumb)
                    listitem.setProperty("widget", smart_shortcuts_data.get("widget", "Addon"))
                    listitem.setProperty("widgetName", item["label"])
                    listitem.setProperty("widgetType", smart_shortcuts_data["type"])

                    if smart_shortcuts_data["type"] == "music" or \
                            smart_shortcuts_data["type"] == "artists" or \
                            smart_shortcuts_data["type"] == "albums" or \
                            smart_shortcuts_data["type"] == "songs":
                        listitem.setProperty("widgetTarget", "music")

                    else:
                        listitem.setProperty("widgetTarget", "videos")

                    listitem.setProperty("widgetPath", smart_shortcuts_data["list"])
                    listings.append(self._get_icon_overrides(tree, listitem, ""))

                else:
                    # Process this as a plugin
                    if item["filetype"] == "directory":
                        thumb = None
                        if item["thumbnail"] != "":
                            thumb = item["thumbnail"]

                        listitem = self.create([item["file"], "%s  >" % item['label'], "", {
                            "icon": "DefaultFolder.png",
                            "thumb": thumb
                        }])
                        listings.append(self._get_icon_overrides(tree, listitem, ""))

                    else:
                        content_type = self._detect_plugin_content(item)
                        if content_type is not None:
                            if addon_type is not None:
                                addon_type = content_type

                            else:
                                if addon_type not in (content_type, 'mixed'):
                                    addon_type = "mixed"

        # Close progress dialog
        dialog.close()

        # Show select dialog
        get_more = self._allow_install_widget_provider(location, is_widget)
        show_dialog = ShowDialog(
            "DialogSelect.xml", CWD, listing=listings, window_title=dialog_label, more=get_more
        )
        show_dialog.doModal()
        selected_item = show_dialog.result
        del show_dialog

        if selected_item == -2:
            # Get more button
            log("Selected get more button")
            return self._explorer_install_widget_provider(history, label, thumbnail,
                                                          item_type, is_widget)

        if selected_item != -1:
            selected_action = listings[selected_item].getProperty("path")
            if selected_action == "::UP::":
                # User wants to go out of explorer, back to select_shortcut
                listitem = xbmcgui.ListItem(label="back", offscreen=True)
                listitem.setProperty("path", "::UP::")

                return listitem

            if selected_action == "::CREATE::":
                # User has chosen the shortcut they want

                # Localize strings
                local_item_type = self.data_func.local(item_type)[2]

                # Create a listitem
                listitem = xbmcgui.ListItem(label=label[len(label) - 1].replace("  >", ""),
                                            label2=local_item_type, offscreen=True)
                listitem.setArt({
                    'icon': "DefaultShortcut.png",
                    'thumb': thumbnail[len(thumbnail) - 1]
                })

                # Build the action
                if item_type in ["32010", "32014", "32069"]:
                    action = 'ActivateWindow(Videos,"%s",return)' % location
                    listitem.setProperty("windowID", "Videos")
                    listitem.setProperty("widgetType", "videos")

                    # Add widget details
                    if is_library:
                        listitem.setProperty("widget", "Library")
                        widget_type = self.node_func.get_media_type(location)
                        if widget_type != "unknown":
                            listitem.setProperty("widgetType", widget_type)

                    else:
                        listitem.setProperty("widget", "Addon")

                    if addon_type is not None:
                        listitem.setProperty("widgetType", addon_type)

                    listitem.setProperty("widgetTarget", "videos")
                    listitem.setProperty("widgetName", dialog_label)
                    listitem.setProperty("widgetPath", location)

                elif item_type in ["32011", "32019", "32073"]:
                    action = 'ActivateWindow(Music,"%s",return)' % location
                    listitem.setProperty("windowID", "Music")

                    # Add widget details
                    listitem.setProperty("widgetType", "audio")
                    if is_library:
                        listitem.setProperty("widget", "Library")
                        widget_type = self.node_func.get_media_type(location)
                        if widget_type != "unknown":
                            listitem.setProperty("widgetType", widget_type)

                    else:
                        listitem.setProperty("widget", "Addon")

                    if addon_type is not None:
                        listitem.setProperty("widgetType", addon_type)

                    listitem.setProperty("widgetTarget", "music")
                    listitem.setProperty("widgetName", dialog_label)
                    listitem.setProperty("widgetPath", location)

                elif item_type in ["32012", "32089"]:
                    action = 'ActivateWindow(Pictures,"%s",return)' % location
                    listitem.setProperty("window_id", "Pictures")

                    # Add widget details
                    listitem.setProperty("widget", "Addon")
                    listitem.setProperty("widgetType", "picture")
                    listitem.setProperty("widgetTarget", "pictures")
                    listitem.setProperty("widgetName", dialog_label)
                    listitem.setProperty("widgetPath", location)

                elif item_type == "32009":
                    action = 'ActivateWindow(Programs,"%s",return)' % location
                    listitem.setProperty("windowID", "Programs")

                    # Add widget details
                    listitem.setProperty("widget", "Addon")
                    listitem.setProperty("widgetType", "program")
                    listitem.setProperty("widgetTarget", "programs")
                    listitem.setProperty("widgetName", dialog_label)
                    listitem.setProperty("widgetPath", location)

                elif item_type == "32123":
                    action = 'ActivateWindow(Games,"%s",return)' % location
                    listitem.setProperty("windowID", "Games")

                    # Add widget details
                    listitem.setProperty("widget", "Addon")
                    listitem.setProperty("widgetType", "game")
                    listitem.setProperty("widgetTarget", "games")
                    listitem.setProperty("widgetName", dialog_label)
                    listitem.setProperty("widgetPath", location)

                else:
                    action = "RunAddon(%s)" % location

                listitem.setProperty("path", action)
                listitem.setProperty("displayPath", action)
                listitem.setProperty("shortcutType", item_type)
                listitem.setProperty("icon", "DefaultShortcut.png")
                if thumbnail[len(thumbnail) - 1] == "":
                    listitem.setProperty("thumbnail", thumbnail[0])
                else:
                    listitem.setProperty("thumbnail", thumbnail[len(thumbnail) - 1])

                listitem.setProperty("location", location)

                return listitem

            if selected_action == "::BACK::":
                # User is going up the heirarchy, remove current level and re-call this function
                history.pop()
                label.pop()
                thumbnail.pop()

                return self.explorer(history, history[len(history) - 1], label, thumbnail,
                                     item_type, is_widget=is_widget)

            if selected_action.startswith("ActivateWindow(") or \
                    selected_action.startswith("$INFO"):
                # The user wants to create a shortcut to a specific shortcut listed
                listitem = listings[selected_item]

                # Add widget details
                if is_library:
                    widget_type = self.node_func.get_media_type(listitem.getProperty("widgetPath"))
                    if widget_type != "unknown":
                        listitem.setProperty("widgetType", widget_type)

                return listitem

            # User has chosen a sub-level to display, add details and re-call this function
            history.append(selected_action)
            label.append(listings[selected_item].getLabel())
            thumbnail.append(listings[selected_item].getProperty("thumbnail"))

            return self.explorer(history, selected_action, label, thumbnail, item_type,
                                 is_widget=is_widget)

        return None

    # ================================
    # === INSTALL WIDGET PROVIDERS ===
    # ================================

    def _explorer_install_widget_provider(self, history, label, thumbnail, item_type, is_widget):
        # CALLED FROM EXPLORER FUNCTION
        # The user has clicked the 'Get More...' button to install additional widget providers
        provider_list = []
        provider_label = []

        # Get widget providers available for install
        for widget_provider in self.widget_providers:
            if widget_provider[1] is None or xbmc.getCondVisibility(widget_provider[1]):
                if not xbmc.getCondVisibility("System.HasAddon(%s)" % (widget_provider[0])):
                    provider_list.append(widget_provider[0])
                    provider_label.append(widget_provider[2])

        # Ask user to select widget provider to install
        selected_provider = xbmcgui.Dialog().select(LANGUAGE(32106), provider_label)

        if selected_provider != -1:
            # User has selected a widget provider for us to install
            self._install_widget_provider(provider_list[selected_provider])

        # Return to where we were
        return self.explorer(history, history[len(history) - 1], label, thumbnail, item_type,
                             is_widget=is_widget)

    def _select_install_widget_provider(self, group, grouping, custom, show_none, current_action):
        # CALLED FROM SELECT FUNCTION
        # The user has clicked the 'Get More...' button to install additional widget providers
        provider_list = []
        provider_label = []

        # Get widget providers available for install
        for widget_provider in self.widget_providers:
            if widget_provider[1] is None or xbmc.getCondVisibility(widget_provider[1]):
                if not xbmc.getCondVisibility("System.HasAddon(%s)" % (widget_provider[0])):
                    provider_list.append(widget_provider[0])
                    provider_label.append(widget_provider[2])

        # Ask user to select widget provider to install
        selected_provider = xbmcgui.Dialog().select(LANGUAGE(32106), provider_label)

        if selected_provider != -1:
            # User has selected a widget provider for us to install
            self._install_widget_provider(provider_list[selected_provider])

        # Return to where we were
        return self.select_shortcut(group=group, grouping=grouping, custom=custom,
                                    show_none=show_none, current_action=current_action)

    def _allow_install_widget_provider(self, location, is_widget, node_allows=None):
        # This function checks whether the 'Get More...' button should be enabled to install
        # additional widget providers

        # Check we're browsing widgets
        if not is_widget:
            return False

        # Check whether we're in skin.helper.service's widgets
        if location is not None and ("script.skin.helper.service" not in location or
                                     self.skinhelper_widget_install is False):
            return False

        # OR check whether node has enabled widget browsing
        if node_allows is not None and node_allows is False:
            return False

        # Check whether the user has the various widget providers installed
        for widget_provider in self.widget_providers:
            if widget_provider[1] is None or xbmc.getCondVisibility(widget_provider[1]):
                if not xbmc.getCondVisibility("System.HasAddon(%s)" % (widget_provider[0])):
                    # The user doesn't have this widget provider installed
                    return True

        # User has all widget providers installed
        return False

    def _install_widget_provider(self, provider):
        xbmc.executebuiltin("InstallAddon(%s)" % provider)
        self._observe_dialogs(["DialogConfirm.xml", "DialogConfirm.xml"])

    def _enable_widget_provider(self, provider):
        xbmc.executebuiltin("EnableAddon(%s)" % provider)
        self._observe_dialogs(["DialogConfirm.xml", "DialogConfirm.xml"])

    @staticmethod
    def _observe_dialogs(dialogs):
        for dialog_xml in dialogs:
            if xbmc.Monitor().waitForAbort(0.5):
                return

            while xbmc.getCondVisibility("Window.IsActive(%s)" % dialog_xml):
                if xbmc.Monitor().waitForAbort(0.5):
                    return

    # ======================
    # === AUTO-PLAYLISTS ===
    # ======================

    def sourcelink_choice(self, selected_shortcut):
        # The user has selected a source. We're going to give them the choice of displaying it
        # in the files view, or view library content from the source
        dialog = xbmcgui.Dialog()

        media_type = None
        negative = None
        window_id = selected_shortcut.getProperty("windowID")
        # Check if we're going to display this in the files view, or the library view
        if window_id == "Videos":
            # Video library
            user_choice = dialog.select(
                LANGUAGE(32078),
                [
                    LANGUAGE(32079),  # Files view
                    LANGUAGE(32015),  # Movies
                    LANGUAGE(32016),  # TV Shows
                    LANGUAGE(32018),  # Music videos
                    LANGUAGE(32081),  # Movies
                    LANGUAGE(32082),  # TV Shows
                    LANGUAGE(32083)  # Music Videos
                ]
            )

            if user_choice == -1:
                return None

            if user_choice == 0:
                # Escape any backslashes (Windows fix)
                new_action = selected_shortcut.getProperty("Path")
                new_action = new_action.replace("\\", "\\\\")
                selected_shortcut.setProperty("Path", new_action)
                selected_shortcut.setProperty("displayPath", new_action)
                return selected_shortcut

            if user_choice == 1:
                media_type = "movies"
                negative = False

            elif user_choice == 2:
                media_type = "tvshows"
                negative = False

            elif user_choice == 3:
                media_type = "musicvideo"
                negative = False

            elif user_choice == 4:
                media_type = "movies"
                negative = True

            elif user_choice == 5:
                media_type = "tvshows"
                negative = True

            elif user_choice == 6:
                media_type = "musicvideo"
                negative = True

        elif window_id == "Music":
            # Music library
            user_choice = dialog.select(
                LANGUAGE(32078),
                [
                    LANGUAGE(32079),  # Files view
                    xbmc.getLocalizedString(134),  # Songs
                    xbmc.getLocalizedString(132),  # Albums
                    xbmc.getLocalizedString(20395),  # Mixed
                    LANGUAGE(32084),  # Songs
                    LANGUAGE(32085),  # Albums
                    LANGUAGE(32086)  # Mixed
                ]
            )
            if user_choice == -1:
                return None

            if user_choice == 0:
                # Escape any backslashes (Windows fix)
                new_action = selected_shortcut.getProperty("Path")
                new_action = new_action.replace("\\", "\\\\")
                selected_shortcut.setProperty("Path", new_action)
                selected_shortcut.setProperty("displayPath", new_action)
                return selected_shortcut

            if user_choice == 1:
                media_type = "songs"
                window_id = "10502"
                negative = False

            elif user_choice == 2:
                media_type = "albums"
                window_id = "10502"
                negative = False

            elif user_choice == 3:
                media_type = "mixed"
                window_id = "10502"
                negative = False

            elif user_choice == 4:
                media_type = "songs"
                window_id = "10502"
                negative = True

            elif user_choice == 5:
                media_type = "albums"
                window_id = "10502"
                negative = True

            elif user_choice == 6:
                media_type = "mixed"
                window_id = "10502"
                negative = True

        else:
            # Pictures
            user_choice = dialog.select(
                LANGUAGE(32078),
                [
                    LANGUAGE(32079),  # Files view
                    xbmc.getLocalizedString(108),  # Slideshow
                    "%s (%s)" %
                    (xbmc.getLocalizedString(108),
                     xbmc.getLocalizedString(590)),  # Slideshow (random)
                    xbmc.getLocalizedString(361),  # Recursive slideshow
                    "%s (%s)" %
                    (xbmc.getLocalizedString(361),
                     xbmc.getLocalizedString(590))  # Recursive slideshow (random)
                ]
            )

            if user_choice == -1:
                return None

            if user_choice == 0:
                # Escape any backslashes (Windows fix)
                new_action = selected_shortcut.getProperty("Path")
                new_action = new_action.replace("\\", "\\\\")
                selected_shortcut.setProperty("Path", new_action)
                selected_shortcut.setProperty("displayPath", new_action)
                return selected_shortcut

            new_action = ""
            if user_choice == 1:
                new_action = "SlideShow(%s,notrandom)" % selected_shortcut.getProperty("location")

            elif user_choice == 2:
                new_action = "SlideShow(%s,random)" % selected_shortcut.getProperty("location")

            elif user_choice == 3:
                new_action = "SlideShow(%s,recursive,notrandom)" % \
                             selected_shortcut.getProperty("location")

            elif user_choice == 4:
                new_action = "SlideShow(%s,recursive,random)" % \
                             selected_shortcut.getProperty("location")

            selected_shortcut.setProperty("path", new_action)
            selected_shortcut.setProperty("displayPath", new_action)

            return selected_shortcut

        # We're going to display it in the library
        filename = self._build_playlist(selected_shortcut.getProperty("location"), media_type,
                                        selected_shortcut.getLabel(), negative)
        new_action = "ActivateWindow(%s,special://profile/addon_data/%s/%s,return)" % \
                     (window_id, ADDON_ID, filename)
        selected_shortcut.setProperty("Path", new_action)
        selected_shortcut.setProperty("displayPath", new_action)

        return selected_shortcut

    def _build_playlist(self, target, mediatype, name, negative):
        # This function will build a playlist that displays the contents of a
        # source in the library view (that is to say, "path" "contains")
        tree = ETree.ElementTree(ETree.Element("smartplaylist"))
        root = tree.getroot()
        root.set("type", mediatype)

        if target.startswith("multipath://"):
            temp_path = target.replace("multipath://", "").split("%2f/")
            target = []
            for item in temp_path:
                if item != "":
                    target.append(url2pathname(item))

        else:
            target = [target]

        ETree.SubElement(root, "name").text = name
        if negative is False:
            ETree.SubElement(root, "match").text = "one"
        else:
            ETree.SubElement(root, "match").text = "all"

        for item in target:
            if negative is False:
                rule = ETree.SubElement(root, "rule")
                rule.set("field", "path")
                rule.set("operator", "startswith")
                ETree.SubElement(rule, "value").text = item

            else:
                rule = ETree.SubElement(root, "rule")
                rule.set("field", "path")
                rule.set("operator", "doesnotcontain")
                ETree.SubElement(rule, "value").text = item

        _id = 1
        while xbmcvfs.exists(os.path.join(DATA_PATH, "%s.xsp" % str(_id))):
            _id += 1

        # Write playlist we'll link to the menu item
        self.data_func.indent(tree.getroot())
        tree.write(os.path.join(DATA_PATH, "%s.xsp" % str(_id)), encoding="utf-8")

        # Add a random property, and save this for use in playlists/backgrounds
        order = ETree.SubElement(root, "order")
        order.text = "random"
        self.data_func.indent(tree.getroot())
        tree.write(os.path.join(DATA_PATH, "%s-randomversion.xsp" % str(_id)), encoding="utf-8")

        return "%s.xsp" % str(_id)

    @staticmethod
    def delete_playlist(target):
        # This function will check if the target links to an auto-generated playlist and,
        # if so, delete it
        if target.startswith("ActivateWindow("):
            try:
                elements = target.split(",")
                if len(elements) > 1:
                    if elements[1].startswith("special://profile/addon_data/%s/" % ADDON_ID) and \
                            elements[1].endswith(".xsp"):
                        xbmcvfs.delete(xbmcvfs.translatePath(elements[1]))
                        xbmcvfs.delete(xbmcvfs.translatePath(
                            elements[1].replace(".xsp", "-randomversion.xsp")
                        ))

            except:
                return

    def rename_playlist(self, target, new_label):
        # This function changes the label tag of an auto-generated playlist

        # First we will check that this is a playlist
        if target.startswith("ActivateWindow("):
            try:
                elements = target.split(",")
            except:
                return

            try:
                if elements[1].startswith("special://profile/addon_data/%s/" % ADDON_ID) and \
                        elements[1].endswith(".xsp"):
                    filename = xbmcvfs.translatePath(elements[1])
                else:
                    return

            except:
                return

            # Load the tree and change the name
            tree = ETree.parse(filename)
            name = tree.getroot().find("name")
            name.text = new_label

            # Write the tree
            self.data_func.indent(tree.getroot())
            tree.write(filename, encoding="utf-8")

            # Load the random tree and change the name
            tree = ETree.parse(filename.replace(".xsp", "-randomversion.xsp"))
            name = tree.getroot().find("name")
            name.text = new_label

            # Write the random tree
            self.data_func.indent(tree.getroot())
            tree.write(filename.replace(".xsp", "-randomversion.xsp"), encoding="utf-8")

    @staticmethod
    def get_images_from_vfs(path):
        # this gets images from a vfs path to be used as backgrounds or icons
        images = []

        json_response = jsonrpc.files_get_directory(path, ["title", "art", "file",
                                                           "fanart", "thumbnail"])

        if json_response:
            json_result = json_response['result']['files']
            for item in json_result:
                label = item["label"]
                image = ""
                if item.get("art"):
                    if "fanart" in item["art"]:
                        image = item["art"]["fanart"]

                    elif "thumb" in item["art"]:
                        image = item["art"]["thumb"]

                if not image and item.get("thumbnail"):
                    image = item["thumbnail"]

                if not image and item.get("file", ""):
                    image = item["file"]

                if image:
                    image = unquote(image)
                    if "$INFO" in image:
                        image = image.replace("image://", "")
                        if image.endswith("/"):
                            image = image[:-1]

                    images.append([image, label])

        return images

    # =====================================
    # === COMMON SELECT SHORTCUT METHOD ===
    # =====================================

    def select_shortcut(self, group="", custom=False, available_shortcuts=None, window_title=None,
                        show_none=False, current_action="", grouping=None):
        # This function allows the user to select a shortcut

        is_widget = False
        if grouping == "widget":
            is_widget = True

        if available_shortcuts is None:
            nodes = self.retrieve_group(group, flat=False, grouping=grouping)
            available_shortcuts = nodes[1]
            window_title = nodes[0]

        else:
            available_shortcuts = self.check_for_folder(available_shortcuts)

        if show_none is not False and group == "":
            available_shortcuts.insert(0, self.create(["::NONE::", LANGUAGE(32053), "", {
                "icon": "DefaultAddonNone.png"
            }]))

        if custom is not False and group == "":
            available_shortcuts.append(self.create(["||CUSTOM||", LANGUAGE(32024), "", {}]))

        if group != "":
            # Add a link to go 'up'
            available_shortcuts.insert(0, self.create(["::BACK::", "..", "", {}]))

        # Show select dialog
        _ = self._allow_install_widget_provider(None, is_widget, self.allow_widget_install)
        show_dialog = ShowDialog("DialogSelect.xml", CWD, listing=available_shortcuts,
                                 window_title=window_title)
        show_dialog.doModal()
        number = show_dialog.result
        del show_dialog

        if number == -2:
            # Get more button
            log("Selected get more button")
            return self._select_install_widget_provider(group, grouping, custom, show_none,
                                                        current_action)

        if number != -1:
            selected_shortcut = available_shortcuts[number]
            path = selected_shortcut.getProperty("Path")
            if path.startswith("::BACK::"):
                # Go back up
                if "," in group:
                    # Remove last level from group
                    new_group = group.rsplit(",", 1)[0]
                else:
                    # We're only one level in, so we'll just clear the group
                    new_group = ""

                # Recall this function
                return self.select_shortcut(group=new_group, grouping=grouping, custom=custom,
                                            show_none=show_none, current_action=current_action)

            if path.startswith("||NODE||"):
                if group == "":
                    group = path.replace("||NODE||", "")
                else:
                    group = "%s,%s" % (group, path.replace("||NODE||", ""))

                return self.select_shortcut(group=group, grouping=grouping, custom=custom,
                                            show_none=show_none, current_action=current_action)
            if path.startswith("||BROWSE||"):
                browse_path = "plugin://%s" % path.replace("||BROWSE||", "")
                selected_shortcut = self.explorer(
                    [browse_path],
                    browse_path,
                    [selected_shortcut.getLabel()],
                    [selected_shortcut.getProperty("thumbnail")],
                    selected_shortcut.getProperty("shortcutType"),
                    is_widget=is_widget
                )

                # Convert backslashes to double-backslashes (windows fix)
                if selected_shortcut is not None:
                    new_action = selected_shortcut.getProperty("Path")
                    new_action = new_action.replace("\\", "\\\\")
                    selected_shortcut.setProperty("Path", new_action)
                    selected_shortcut.setProperty("displayPath", new_action)

            elif path.startswith("||VIDEO||"):
                # Video node
                selected_shortcut = self.explorer(
                    [path.replace("||VIDEO||", "")],
                    path.replace("||VIDEO||", ""),
                    [selected_shortcut.getLabel()],
                    [selected_shortcut.getProperty("thumbnail")],
                    "32014",
                    is_widget=is_widget)

                # Convert backslashes to double-backslashes (windows fix)
                if selected_shortcut is not None:
                    new_action = selected_shortcut.getProperty("Path")
                    new_action = new_action.replace("\\", "\\\\")
                    selected_shortcut.setProperty("Path", new_action)
                    selected_shortcut.setProperty("displayPath", new_action)

            elif path.startswith("||AUDIO||"):
                # Audio node
                selected_shortcut = self.explorer(
                    [path.replace("||AUDIO||", "")],
                    path.replace("||AUDIO||", ""),
                    [selected_shortcut.getLabel()],
                    [selected_shortcut.getProperty("thumbnail")],
                    "32019",
                    is_widget=is_widget
                )

                # Convert backslashes to double-backslashes (windows fix)
                if selected_shortcut is not None:
                    new_action = selected_shortcut.getProperty("Path")
                    new_action = new_action.replace("\\", "\\\\")
                    selected_shortcut.setProperty("Path", new_action)
                    selected_shortcut.setProperty("displayPath", new_action)

            elif path == "||UPNP||":
                selected_shortcut = self.explorer(
                    ["upnp://"],
                    "upnp://",
                    [selected_shortcut.getLabel()],
                    [selected_shortcut.getProperty("thumbnail")],
                    selected_shortcut.getProperty("shortcutType"),
                    is_widget=is_widget
                )

            elif path.startswith("||SOURCE||"):
                selected_shortcut = self.explorer(
                    [path.replace("||SOURCE||", "")],
                    path.replace("||SOURCE||", ""),
                    [selected_shortcut.getLabel()],
                    [selected_shortcut.getProperty("thumbnail")],
                    selected_shortcut.getProperty("shortcutType"),
                    is_widget=is_widget)

                if selected_shortcut is None or "upnp://" in selected_shortcut.getProperty("Path"):
                    return selected_shortcut

                if is_widget:
                    # Set widget to 'source'
                    selected_shortcut.setProperty("widget", "source")
                else:
                    # Find out what the user wants to do with the source
                    selected_shortcut = self.sourcelink_choice(selected_shortcut)

            elif path.startswith("::PLAYLIST"):
                log("Selected playlist")
                if is_widget:
                    # Return actionShow as chosenPath
                    selected_shortcut.setProperty("chosenPath",
                                                  selected_shortcut.getProperty("action-show"))

                elif ">" not in path or "Videos" in path:
                    # Give the user the choice of playing or displaying the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.yesno(LANGUAGE(32040), LANGUAGE(32060),
                                              LANGUAGE(32061), LANGUAGE(32062))
                    # False: Display
                    # True: Play
                    if not userchoice:
                        selected_shortcut.setProperty("chosenPath",
                                                      selected_shortcut.getProperty("action-show"))
                    else:
                        selected_shortcut.setProperty("chosenPath",
                                                      selected_shortcut.getProperty("action-play"))

                elif ">" in path:
                    # Give the user the choice of playing, displaying or party more for the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.select(
                        LANGUAGE(32060),
                        [LANGUAGE(32061),
                         LANGUAGE(32062),
                         xbmc.getLocalizedString(589)]
                    )
                    # 0 - Display
                    # 1 - Play
                    # 2 - Party mode
                    if not userchoice or userchoice == 0:
                        selected_shortcut.setProperty("chosenPath",
                                                      selected_shortcut.getProperty("action-show"))

                    elif userchoice == 1:
                        selected_shortcut.setProperty("chosenPath",
                                                      selected_shortcut.getProperty("action-play"))

                    else:
                        selected_shortcut.setProperty("chosenPath",
                                                      selected_shortcut.getProperty("action-party"))

            elif path.startswith("::INSTALL::"):
                # Try to automatically install an addon
                self._install_widget_provider(path.replace("::INSTALL::", ""))

                # Re-call this function
                return self.select_shortcut(group=group, grouping=grouping, custom=custom,
                                            show_none=show_none, current_action=current_action)

            elif path.startswith("::ENABLE::"):
                # Try to automatically enable an addon
                self._enable_widget_provider(path.replace("::ENABLE::", ""))

                # Re-call this function
                return self.select_shortcut(group=group, grouping=grouping, custom=custom,
                                            show_none=show_none, current_action=current_action)

            elif path == "||CUSTOM||":
                # Let the user type a command
                keyboard = xbmc.Keyboard(current_action, LANGUAGE(32027), False)
                keyboard.doModal()
                selected_shortcut = None
                if keyboard.isConfirmed():
                    action = keyboard.getText()
                    if action != "":
                        # Create a really simple listitem to return
                        selected_shortcut = xbmcgui.ListItem('', LANGUAGE(32024), offscreen=True)
                        selected_shortcut.setProperty("Path", action)
                        selected_shortcut.setProperty("custom", "true")

            elif path == "::NONE::":
                # Create a really simple listitem to return
                selected_shortcut = xbmcgui.ListItem("::NONE::", offscreen=True)

            # Check that explorer hasn't sent us back here
            if selected_shortcut is not None and selected_shortcut.getProperty("path") == "::UP::":
                return self.select_shortcut(group=group, custom=custom, available_shortcuts=None,
                                            window_title=window_title, show_none=show_none,
                                            grouping=grouping, current_action=current_action)

            return selected_shortcut

        return None

    # ==============================
    # === WIDGET RELOAD FUNCTION ===
    # ==============================

    # With gui 312, we're finding a number of plugins aren't returning updated content after
    # media is played. This function adds a widgetReload property - managed by Skin Helper Widgets
    # - to plugins to help display updated content

    @staticmethod
    def add_widget_reload(widget_path):
        if "plugin://" not in widget_path or "reload=" in widget_path.lower() or \
                "script.extendedinfo" in widget_path.lower():
            # Not a plugin, or already has a reload parameter
            # Also return on Extended Info, as it doesn't like its parameters to be altered
            return widget_path

        # Depending whether it already has additional components or not, we may need to use
        # a ? or a & to extend the path with the new reload parameter
        reload_splitter = "?"
        if "?" in widget_path:
            reload_splitter = "&"

        # We have seperate reload params for each content type
        # default: refresh at every library change/video playback (widgetreload) +
        # every 10 minutes (widgetreload2)
        reload_param = \
            "$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"

        if "movie" in widget_path:
            reload_param = "$INFO[Window(Home).Property(widgetreload-movies)]"

        elif "episode" in widget_path:
            reload_param = "$INFO[Window(Home).Property(widgetreload-episodes)]"

        elif "tvshow" in widget_path:
            reload_param = "$INFO[Window(Home).Property(widgetreload-episodes)]"

        elif "musicvideo" in widget_path:
            reload_param = "$INFO[Window(Home).Property(widgetreload-musicvideos)]"

        elif "music" in widget_path or "song" in widget_path:
            reload_param = "$INFO[Window(Home).Property(widgetreload-music)]"

        # And return it all
        return "%s%sreload=%s" % (widget_path, reload_splitter, reload_param)

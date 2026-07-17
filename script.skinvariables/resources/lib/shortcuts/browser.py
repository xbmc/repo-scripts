# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem, Dialog
from resources.lib.kodiutils import get_localized


SHORTCUT_CONFIG = 'skinvariables-shortcut-config.json'
SHORTCUT_FOLDER = 'special://skin/shortcuts/'
PLAYLIST_EXT = ('.xsp', '.m3u', '.m3u8', '.strm', '.wpl')
NO_FOLDER_ITEM = ('grouping://', 'plugin://script.skinvariables/?info=set_filter_dir')


def _ask_is_playable(path):
    return Dialog().yesno(
        get_localized(32050),  # Add playlist
        f'{path}\n{get_localized(32051)}',  # Add playlist as playable shortcut or browesable directory
        yeslabel=get_localized(208),  # Play
        nolabel=get_localized(1024)  # Browse
    )


class GetDirectoryBrowser():
    def __init__(self, use_details=True, item_prefix=None, use_rawpath=False, allow_links=True, folder_name=None):
        self.history = []
        self.filepath = f'{SHORTCUT_FOLDER}{SHORTCUT_CONFIG}'
        self.item_prefix = item_prefix or ''
        self.use_details = use_details
        self.use_rawpath = use_rawpath
        self.allow_links = allow_links
        self.folder_name = folder_name or f'{get_localized(32052)}...'
        self.heading_str = ''

    @property
    def definitions(self):
        try:
            return self._definitions
        except AttributeError:
            from resources.lib.shortcuts.futils import read_meta_from_file
            self._definitions = read_meta_from_file(self.filepath)
            return self._definitions

    @staticmethod
    def get_formatted_path(path, node=None, link=True):
        if not path:
            return ('', '')
        if node and not link and path.endswith(PLAYLIST_EXT) and _ask_is_playable(path):
            return (f'PlayMedia({path})', '')
        if (not node) is not (not link):  # XOR: Links without nodes return raw path; Folders with nodes return raw path (+ node)
            return (path, node)
        if path.startswith('script://'):
            path = path.replace('script://', '')
            return (f'RunScript({path})', '')
        if path.startswith('androidapp://'):
            path = path.replace('androidapp://', '')
            return (f'StartAndroidActivity({path})', '')
        return (f'PlayMedia({path})', '')

    def get_formatted_item(self, name, path, icon, node=None, link=True):
        if node == 'link':
            link = True
            node = ''
        path, target = self.get_formatted_path(path, node, link) if not self.use_rawpath else (path, node)
        item = {"label": name or '', "path": path or '', "icon": icon or '', "target": target or ''}
        # from resources.lib.shortcuts.futils import dumps_log_to_file
        # dumps_log_to_file({'name': name, 'path': path, 'icon': icon, 'node': node, 'item': item}, filename=f'{name}.json')
        return item

    def get_new_item(self, item, allow_browsing=True):
        from jurialmunkey.parser import boolean
        # Update to new item values
        icon = item[1].getArt('thumb') or ''
        node = item[1].getProperty('nodetype') or None
        name = item[1].getProperty('nodename') or item[1].getLabel() or ''
        link = not boolean(item[1].getProperty('isfolder') or False)
        path = item[0] or ''

        # If the item is a folder then we open it otherwise return formatted item
        if allow_browsing and item[2]:
            return self.get_directory(path, icon, name, item, True)
        return self.get_formatted_item(name, path, icon, node, link)

    def get_items(self, directory, path, icon, name, item, add_item=False):
        directory_items = [i for i in directory.items if self.allow_links or i[2]]  # All items if allow links otherwise filter for folders only

        if add_item and path and not path.startswith(NO_FOLDER_ITEM):
            li = ListItem(label=self.folder_name, label2=path, path=path, offscreen=True)
            li.setArt({'icon': icon, 'thumb': icon})
            li.setProperty('isfolder', 'True')
            li.setProperty('nodename', name)
            li.setProperty('nodetype', item[1].getProperty('nodetype') or '')
            directory_items.insert(0, (path, li, False, ))

        self.heading_str = name or path
        items = [i[1] for i in directory_items if i]
        x = Dialog().select(heading=self.heading_str, list=items, useDetails=self.use_details)
        if x != -1:
            item = directory_items[x]
            self.history.append((directory, path, icon, name, item, True, )) if item[2] else None  # Add old values to history before updating
            return self.get_new_item(item)
        try:
            return self.get_items(*self.history.pop())
        except IndexError:
            return []

    def get_directory(self, path='grouping://shortcuts/', icon='', name='Shortcuts', item=None, add_item=False):
        if not path:
            return

        from resources.lib.shortcuts.grouping import GetDirectoryGrouping
        DirectoryClass = GetDirectoryGrouping

        if not path.startswith('grouping://'):
            from resources.lib.shortcuts.jsonrpc import GetDirectoryJSONRPC
            DirectoryClass = GetDirectoryJSONRPC

        directory = DirectoryClass(path, definitions=self.definitions, target=item[1].getProperty('nodetype') if item else None)
        if not directory.items and not add_item:
            return

        if not item:
            li = ListItem(label=name, label2=path, path=path, offscreen=True)
            li.setArt({'icon': icon, 'thumb': icon})
            li.setProperty('nodename', name)
            item = (path, li, True, )

        return self.get_items(directory, path, icon, name, item, add_item)
